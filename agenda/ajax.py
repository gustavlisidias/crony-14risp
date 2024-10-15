import os

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.http import JsonResponse
from django.utils import timezone
from django.utils.timezone import make_aware

from datetime import datetime, timedelta
from pathlib import Path

from agenda.models import (
	Atividade,
	Ferias,
	DocumentosFerias,
	SolicitacaoFerias,
	TipoAtividade,
)
from agenda.utils import ferias_funcionarios
from configuracoes.models import Variavel
from funcionarios.models import Documento, TipoDocumento, JornadaFuncionario
from ponto.models import Ponto
from web.utils import not_none_not_empty, add_coins


class InvalidPeriodVacation(Exception):
	def __init__(self, **kwargs):
		funcionario, inicio, final, saldo = kwargs.get('funcionario'), kwargs.get('inicio'), kwargs.get('final'), kwargs.get('saldo')
		message = f'Não foi possível encontrar férias disponíveis para o periodo {inicio} até {final} com saldo de {saldo} dias para o funcionario {funcionario}'
		super().__init__(message)


@login_required(login_url='entrar')
def MoverEventoView(request):
	if request.method != 'POST':
		return JsonResponse({'message': 'Método não permitido!'}, status=404)

	pk = int(request.POST.get('id'))
	titulo = request.POST.get('title')
	inicio = request.POST.get('start')
	final = request.POST.get('end')

	if not_none_not_empty(pk, titulo, inicio, final):
		try:
			atividade = Atividade.objects.get(pk=pk, titulo=titulo)
			atividade.inicio = make_aware(datetime.strptime(inicio, '%Y-%m-%d'))
			atividade.final = make_aware(datetime.strptime(final, '%Y-%m-%d') - timedelta(days=1)) if final != 'Invalid date' else None
			atividade.save()
				
			data = {
				'message': 'Evento alterado com sucesso!',
				'id': pk,
				'inicio': inicio,
				'final': (datetime.strptime(final, '%Y-%m-%d') - timedelta(days=1)).strftime('%Y-%m-%d')
			}
			
			return JsonResponse(data, status=200)

		except Exception as e:
			return JsonResponse({'message': f'Evento não foi movido: {e}'}, status=400)

	else:
		return JsonResponse({'message': 'Preencha todos os campos!'}, status=404)


@login_required(login_url='entrar')
def EditarEventoView(request):
	pk = int(request.POST.get('id'))
	titulo = request.POST.get('titulo')
	descricao = request.POST.get('descricao')
	tipo = request.POST.get('tipo')
	inicio = request.POST.get('inicio')
	final = request.POST.get('final')
	usuarios = request.POST.getlist('usuarios')
	finalizado = request.POST.get('finalizado')

	if not_none_not_empty(pk, titulo, descricao, tipo, inicio, usuarios):
		try:
			with transaction.atomic():
				atividade = Atividade.objects.get(pk=pk)
				atividade.titulo = titulo
				atividade.descricao = descricao
				atividade.tipo = TipoAtividade.objects.get(pk=tipo)
				atividade.inicio = make_aware(datetime.strptime(inicio, '%Y-%m-%d'))
				atividade.final = make_aware(datetime.strptime(final, '%Y-%m-%d')) if final != '' else None
				atividade.funcionarios.set(usuarios)
				atividade.data_finalizacao = timezone.localtime(timezone.now()) if finalizado else None
				atividade.save()

				if not_none_not_empty(request.POST.get('recorrente')):
					atividades = Atividade.objects.filter(recorrencia=pk)
					for recorrencia in atividades:
						recorrencia.titulo = titulo
						recorrencia.descricao = descricao
						recorrencia.tipo = TipoAtividade.objects.get(pk=tipo)
						recorrencia.funcionarios.set(usuarios)
						recorrencia.data_finalizacao = timezone.localtime(timezone.now()) if finalizado else None
						recorrencia.save()

				if finalizado:
					for funcionario in atividade.funcionarios.all():
						add_coins(funcionario, 20)

				if finalizado and atividade.tipo.slug == 'ferias':
					# Ao finalizar a atividade, a férias é consumada
					solicitacao = SolicitacaoFerias.objects.get(pk=atividade.solic_ferias.pk)
					delta = atividade.final.date() - atividade.inicio.date()
					dados_ferias = ferias_funcionarios(solicitacao.funcionario).get(solicitacao.funcionario.nome_completo, [])

					# Preciso consultar o estado atual de saldos por período do funcionário
					# No periodo cadastrado preciso que haja saldo suficiente
					resultado = [i for i in dados_ferias if i['vencimento'] <= solicitacao.final_periodo and i['inicio'] >= solicitacao.inicio_periodo and i['saldo'] >= delta][0]

					if resultado:
						Ferias(
							funcionario=solicitacao.funcionario,
							ano_referencia=resultado['periodo'],
							inicio_periodo=solicitacao.inicio_periodo,
							final_periodo=solicitacao.final_periodo,
							inicio_ferias=atividade.inicio,
							final_ferias=atividade.final,
							abono=solicitacao.abono,
							decimo=solicitacao.decimo,
						).save()
					else:
						raise InvalidPeriodVacation(funcionario=solicitacao.funcionario.nome_completo, inicio=atividade.inicio.date(), final=atividade.final.date(), saldo=delta.days)

					# Abonar dias não trabalhados nas férias
					Ponto.objects.filter(
						funcionario=solicitacao.funcionario,
						data__gte=solicitacao.inicio_ferias,
						data__lte=solicitacao.final_ferias,
					).delete()
					
					jornadas = JornadaFuncionario.objects.filter(funcionario=solicitacao.funcionario, final_vigencia=None).order_by('funcionario__id', 'dia', 'ordem')
					data_inicial = solicitacao.inicio_ferias

					while data_inicial <= solicitacao.final_ferias:
						weekday = 1 if data_inicial.weekday() + 2 == 8 else data_inicial.weekday() + 2
						data = data_inicial

						for jornada in jornadas.filter(dia=weekday):
							Ponto(
								funcionario=solicitacao.funcionario,
								data=data,
								hora=jornada.hora,
								alterado=True,
							).save()

						data_inicial += timedelta(days=1)

				message = 'Evento finalizado com sucesso!' if finalizado else 'Evento alterado com sucesso!'
				messages.success(request, message)
				return JsonResponse({'message': 'success'}, status=200)

		except Exception as e:
			messages.error(request, f'Evento não foi alterado: {e}')
			return JsonResponse({'message': e}, status=400)

	else:
		messages.warning(request, 'Preencha todos os campos obrigatórios!')
		return JsonResponse({'message': 'forbidden'}, status=404)


@login_required(login_url='entrar')
def ProcurarDocumentosFeriasView(request, solic):
	if not request.method == 'GET':
		messages.warning(request, 'Método não permitido!')
		return JsonResponse({'message': 'forbidden'}, status=404)

	try:
		solicitacao = SolicitacaoFerias.objects.get(pk=solic)
		documentos = DocumentosFerias.objects.filter(solicitacao=solicitacao)

		if solicitacao:
			data = {
				'id': solicitacao.id,
				'nome': solicitacao.funcionario.nome_completo,
				'observacao': solicitacao.observacao,
				'inicio': solicitacao.inicio_ferias,
				'final': solicitacao.final_ferias,
				'abono': solicitacao.abono or 0,
				'decimo': '13º solicitado' if solicitacao.decimo else '13º não solicitado',
				'docs': list(documentos.values('id', 'caminho')),
			}
			return JsonResponse(data, safe=False, status=200)
		
		else:
			return JsonResponse({}, safe=False, status=200)

	except Exception as e:
		messages.error(request, f'Solicitação de férias não foi removida! {e}')
		return JsonResponse({'message': e}, status=400)


@login_required(login_url='entrar')
def ExcluirSolicitacaoFeriasView(request, solic):
	if request.method != 'POST':
		messages.warning(request, 'Método não permitido!')
		return JsonResponse({'message': 'forbidden'}, status=404)

	try:
		SolicitacaoFerias.objects.get(pk=solic).delete()
		messages.success(request, 'Solicitação de férias removida com sucesso!')
		return JsonResponse({'message': 'success'}, status=200)

	except Exception as e:
		messages.error(request, f'Solicitação de férias não foi removida! {e}')
		return JsonResponse({'message': e}, status=400)


@login_required(login_url='entrar')
def AprovarSolicitacaoFeriasView(request, solic):
	if request.method != 'POST':
		messages.warning(request, 'Método não permitido!')
		return JsonResponse({'message': 'forbidden'}, status=404)

	try:
		with transaction.atomic():
			# Aprovar a solicitação
			solicitacao = SolicitacaoFerias.objects.get(pk=solic)
			solicitacao.status = True
			solicitacao.save()

			# Enviar documentos de férias para a documentação do funcionario
			documentos = DocumentosFerias.objects.filter(solicitacao=solicitacao)
			if documentos:
				for documento in documentos:
					Documento.objects.create(
						funcionario=solicitacao.funcionario,
						tipo=TipoDocumento.objects.get(codigo='037'), # Aviso De Ferias - 037
						documento=documento.documento,
						caminho=documento.caminho,
						data_documento=timezone.localdate(),
					)
				
					# Salvo os documentos na pasta do funcionario
					pasta = Path(Variavel.objects.get(chave='PATH_DOCS_EMP').valor, f'{solicitacao.funcionario.matricula} - {solicitacao.funcionario.nome_completo}')
					os.makedirs(pasta, exist_ok=True)
					caminho = os.path.join(pasta, f'{documento.caminho}.pdf')

					with open(caminho, 'wb') as f:
						f.write(documento.documento)

			# Criar agenda de férias
			atividade = Atividade.objects.create(
				titulo=f'Férias {solicitacao.funcionario}',
				descricao=f"Férias do funcinário {solicitacao.funcionario} do período de {solicitacao.inicio_ferias.strftime('%d/%m/%Y')} até {solicitacao.final_ferias.strftime('%d/%m/%Y')}<br>Observações: {solicitacao.observacao}",
				tipo=TipoAtividade.objects.get(slug='ferias'),
				inicio=make_aware(datetime.combine(solicitacao.inicio_ferias, datetime.min.time())),
				final=make_aware(datetime.combine(solicitacao.final_ferias, datetime.min.time())),
				autor=solicitacao.funcionario,
				solic_ferias=solicitacao
			)
			atividade.funcionarios.set([solicitacao.funcionario.id])

			messages.success(request, 'Solicitação de férias aprovada com sucesso!')
			return JsonResponse({'message': 'success'}, status=200)

	except Exception as e:
		messages.error(request, f'Solicitação de férias não foi aprovada! {e}')
		return JsonResponse({'message': e}, status=400)
