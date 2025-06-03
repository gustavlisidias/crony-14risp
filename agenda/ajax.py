import os

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.mail import send_mail
from django.db import transaction
from django.http import JsonResponse
from django.shortcuts import redirect
from django.utils import timezone
from django.utils.timezone import make_aware

from datetime import datetime, timedelta, time
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
from funcionarios.models import Funcionario, Documento, TipoDocumento, Setor
from notifications.signals import notify
from ponto.models import Ponto, Saldos
from ponto.utils import filtrar_abonos, total_saldo
from web.utils import not_none_not_empty, add_coins  # noqa: F401


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

				# if finalizado:
				# 	for funcionario in atividade.funcionarios.all():
				# 		add_coins(funcionario, 20, 'Finalização de atividade')

				if finalizado and atividade.tipo.slug == 'ferias':
					# Ao finalizar a atividade, a férias é consumada
					solicitacao = SolicitacaoFerias.objects.get(pk=atividade.solic_ferias.pk)
					delta = atividade.final.date() - atividade.inicio.date()
					dados_ferias = ferias_funcionarios(solicitacao.funcionario).get(solicitacao.funcionario, [])

					# Preciso consultar o estado atual de saldos por período do funcionário
					# No periodo cadastrado preciso que haja saldo suficiente
					resultado = [i for i in dados_ferias if i['vencimento'] <= solicitacao.final_periodo and i['inicio'] >= solicitacao.inicio_periodo and i['saldo'] >= delta]
					if not resultado:
						resultado = [i for i in dados_ferias if i['saldo'] >= delta]

					if resultado:
						Ferias(
							funcionario=solicitacao.funcionario,
							ano_referencia=resultado[0]['periodo'],
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

					jornada_para_abonar = filtrar_abonos(atividade.inicio, atividade.final, solicitacao.funcionario)
					for dia, pontos in jornada_para_abonar.items():
						Ponto(
							funcionario=solicitacao.funcionario,
							data=dia,
							hora=time(),
							motivo='Férias',
							alterado=True,
							encerrado=True,
							autor_modificacao=Funcionario.objects.get(usuario=request.user)
						).save()

						if dia.weekday() not in [5, 6]:
							Saldos(
								funcionario=solicitacao.funcionario,
								saldo=total_saldo(pontos),
								data=dia
							).save()

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
				'status_label': solicitacao.get_status,
				'status': solicitacao.status
			}
			return JsonResponse(data, safe=False, status=200)
		
		else:
			return JsonResponse({}, safe=False, status=200)

	except Exception as e:
		messages.error(request, f'Solicitação de férias não foi removida! {e}')
		return JsonResponse({'message': e}, status=400)


@login_required(login_url='entrar')
def AlterarSolicitacaoFeriasView(request, solic):
	if request.method != 'POST':
		messages.warning(request, 'Método não permitido!')
		return redirect('ferias')

	try:
		status = int(request.POST.get('novo_stauts'))
		solicitacao = SolicitacaoFerias.objects.get(pk=solic)

		if solicitacao.aprovador.usuario != request.user and request.user.get_access != 'admin':
			messages.warning(request, 'Você não tem permissão para alterar o status')
			return redirect('ferias')

		with transaction.atomic():
			if status == SolicitacaoFerias.Status.APROVADO:
				# Se não possui mais fluxo, vai para aprovação final
				if solicitacao.aprovador == Setor.objects.get(setor='Recursos Humanos').responsavel:
					# Alterar status para aprovado
					solicitacao.status = status
					solicitacao.save()
					
					# Enviar documentos de férias para a documentação do funcionario
					documentos = DocumentosFerias.objects.filter(solicitacao=solicitacao)
					if documentos:
						for documento in documentos:					
							# Salvo os documentos na pasta do funcionario
							pasta = Path(Variavel.objects.get(chave='PATH_DOCS_EMP').valor, f'{solicitacao.funcionario.matricula} - {solicitacao.funcionario.nome_completo}')
							os.makedirs(pasta, exist_ok=True)

							data_documento = timezone.localdate()
							tipo = TipoDocumento.objects.get(slug='ferias')
							caminho = os.path.join(pasta, f'{data_documento.strftime("%Y-%m-%d")}_{tipo.codigo}_{documento.caminho}')

							with open(caminho, 'wb') as f:
								f.write(documento.documento)

							Documento.objects.create(
								funcionario=solicitacao.funcionario,
								tipo=tipo,
								caminho=caminho,
								data_documento=data_documento,
							)

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

					notify.send(
						sender=request.user,
						recipient=Setor.objects.get(setor='Financeiro').responsavel.usuario,
						verb=f'As férias de {solicitacao.funcionario} foram aprovadas. Alinhar pendencias e demandas com o setor de Recursos Humanos.',
					)

					send_mail(
						'Crony - Aprovação de Férias',
						f'As férias de {solicitacao.funcionario} foram aprovadas. Alinhar pendencias e demandas com o setor de Recursos Humanos.',
						'avisos@novadigitalizacao.com.br',
						[Setor.objects.get(setor='Financeiro').responsavel.email],
						fail_silently=False,
					)

					messages.success(request, 'Solicitação de férias aprovada com sucesso!')
				
				else:
					aprovador_anterior = solicitacao.aprovador
					aprovador_atual = Funcionario.objects.get(usuario=request.user)
					aprovador_novo = solicitacao.aprovador.gerente or Setor.objects.get(setor='Recursos Humanos').responsavel

					# Alterar status para pendente e passar para proximo aprovador
					solicitacao.status = SolicitacaoFerias.Status.PENDENTE
					solicitacao.aprovador = aprovador_novo
					solicitacao.save()

					notify.send(
						sender=aprovador_atual.usuario,
						recipient=aprovador_novo.usuario,
						verb=f'Você possui uma nova solicitação de férias de {solicitacao.funcionario}. Aprovada anteriormente por {aprovador_atual} (RU) - {aprovador_anterior} (AP).',
					)

					send_mail(
						'Crony - Solicitação de Férias',
						f'Você possui uma nova solicitação de férias de {solicitacao.funcionario}. Aprovada anteriormente por {aprovador_atual} (RU) - {aprovador_anterior} (AP).',
						'avisos@novadigitalizacao.com.br',
						[aprovador_novo.email],
						fail_silently=False,
					)

					messages.success(request, 'Solicitação de férias aprovada com sucesso. Enviada para próximo aprovador.')
				
			else:
				# Alterar status
				solicitacao.status = status
				solicitacao.save()
				messages.success(request, 'Solicitação de férias alterada com sucesso!')

		notify.send(
			sender=request.user,
			recipient=solicitacao.funcionario.usuario,
			verb=f'Sua solicitação de férias foi atualizada: {solicitacao.get_status}',
		)

	except Exception as e:
		messages.error(request, f'Solicitação de férias não foi alterada! {e}')

	return redirect('ferias')
