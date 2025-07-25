import codecs
import pandas as pd

from datetime import datetime, timedelta

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.mail import send_mail
from django.db import transaction
from django.db.models import Q
from django.http import HttpResponse, HttpResponseRedirect
from django.shortcuts import redirect, render
from django.utils import timezone
from django.utils.timezone import make_aware

from agenda.models import (
	Atividade,
	DocumentosFerias,
	SolicitacaoFerias,
	TipoAtividade,
	Avaliacao,
)
from agenda.utils import ferias_funcionarios
from configuracoes.models import Variavel
from funcionarios.models import Funcionario
from funcionarios.utils import converter_documento
from notifications.signals import notify
from ponto.renderers import RenderToPDF
from web.decorators import base_context_required
from web.utils import not_none_not_empty, add_coins
from web.views import ADMIN_USER


# Page
@base_context_required
def AgendaView(request, context):
	funcionario = context['funcionario']
	# colaboradores = funcionarios

	atividades = Atividade.objects.all().order_by('inicio')
	tipos = TipoAtividade.objects.all()

	if request.user.get_access == 'common':
		funcionarios = funcionarios.filter(pk=funcionario.pk)
		atividades = atividades.filter(Q(funcionarios=funcionario) | Q(tipo__slug='ferias') | Q(tipo__slug='sala-reuniao'))

	if request.user.get_access == 'manager':
		funcionarios = funcionarios.filter(Q(gerente=funcionario) | Q(pk=funcionario.pk)).distinct()
		atividades = atividades.filter(Q(funcionarios__gerente=funcionario) | Q(funcionarios=funcionario) | Q(tipo__slug='ferias') | Q(tipo__slug='sala-reuniao')).distinct()

	listagem = [{
		'id': str(i.id),
		'title': i.titulo,
		'description': i.descricao,
		'type': [{'id': str(i.tipo.id), 'name': i.tipo.tipo}],
		'start': i.inicio.strftime('%Y-%m-%d'),
		'end': (i.final + timedelta(days=1)).strftime('%Y-%m-%d'),
		'inicio': i.inicio.strftime('%Y-%m-%d'),
		'final': i.final.strftime('%Y-%m-%d'),
		'autor': i.autor.nome_completo,
		'cadastro': i.data_cadastro.strftime('%d de %B de %Y'),
		'users': [{'id': str(j.id), 'name': j.nome_completo} for j in i.funcionarios.all()],
		'backgroundColor': i.tipo.cor if not i.data_finalizacao else '#aaa',
		'borderColor': i.tipo.cor if not i.data_finalizacao else '#aaa',
		'concluido': '1' if i.data_finalizacao else '0',
		'recorrente': i.recorrencia.id if i.recorrencia else None
	} for i in atividades]

	context.update({
		# 'colaboradores': colaboradores,
		'atividades': atividades,
		'listagem': listagem,
		'tipos': tipos
	})

	return render(request, 'pages/agenda.html', context)


# Modal
@login_required(login_url='entrar')
def AdicionarAtividadeView(request):
	if request.method != 'POST':
		messages.warning(request, 'Método não permitido!')
		return redirect('inicio')

	titulo = request.POST.get('titulo')
	tipo = request.POST.get('tipo')
	descricao = request.POST.get('descricao')
	inicio = request.POST.get('inicio')
	final = request.POST.get('final')
	usuarios = request.POST.getlist('usuarios')
	recorrencia = request.POST.get('recorrencia', 'none')
	final_recorrencia = request.POST.get('recorrencia_final')
	autor = Funcionario.objects.get(usuario=request.user)

	if not_none_not_empty(titulo, descricao, inicio, usuarios, autor):
		try:
			if recorrencia != 'none':
				inicio_dt = make_aware(datetime.strptime(inicio, '%Y-%m-%d'))
				final_dt = make_aware(datetime.strptime(final, '%Y-%m-%d')) if final != '' else None
				final_recorrencia_dt = make_aware(datetime.strptime(final_recorrencia, '%Y-%m-%d')) if final_recorrencia != '' else None

				delta = {
					'none': None,
					'daily': timedelta(days=1),
					'weekly': timedelta(weeks=1),
					'biweekly': timedelta(weeks=2),
					'monthly': timedelta(weeks=4),
				}[recorrencia]

				primeira_atividade = None
				while True:
					atividade = Atividade.objects.create(
						titulo=titulo,
						descricao=descricao,
						tipo=TipoAtividade.objects.get(pk=tipo),
						inicio=inicio_dt,
						final=final_dt,
						autor=autor
					)

					if not primeira_atividade:
						primeira_atividade = atividade

					atividade.recorrencia = primeira_atividade
					atividade.funcionarios.set(usuarios)
					atividade.save()

					if delta is None or (inicio_dt + delta) > final_recorrencia_dt:
						break

					inicio_dt += delta
					if final_dt:
						final_dt += delta
			else:
				atividade = Atividade.objects.create(
					titulo=titulo,
					descricao=descricao,
					tipo=TipoAtividade.objects.get(pk=tipo),
					inicio=datetime.strptime(inicio, '%Y-%m-%d'),
					final=datetime.strptime(final, '%Y-%m-%d') if not_none_not_empty(final) else datetime.strptime(inicio, '%Y-%m-%d'),
					autor=autor
				)

				atividade.funcionarios.set(usuarios)
				atividade.save()

			# add_coins(Funcionario.objects.get(usuario=request.user), 10, 'Criação de atividade')
			messages.success(request, 'Atividade criada com sucesso!')

		except Exception as e:
			messages.error(request, f'Atividade não foi criada! {e}')

	else:
		messages.error(request, 'Preencha todos os campos!')

	return HttpResponseRedirect(request.META.get('HTTP_REFERER', '/'))


# Page
@base_context_required
def FeriasView(request, context):
	funcionarios = context['funcionarios']
	funcionario = context['funcionario']

	ferias = ferias_funcionarios(funcionarios)
	statuses = [{'key': i[0], 'value': i[1]} for i in SolicitacaoFerias.Status.choices if i[0] != 0]

	# Filtro de solicitações por role
	if funcionario.usuario.get_access == 'common':
		solicitacoes = SolicitacaoFerias.objects.filter(funcionario=funcionario)
	elif funcionario.usuario.get_access == 'manager':
		solicitacoes = SolicitacaoFerias.objects.filter(Q(funcionario=funcionario) | Q(aprovador=funcionario)).distinct()
	else:
		solicitacoes = SolicitacaoFerias.objects.all()
	
	if request.method == 'POST':
		inicio_ferias = request.POST.get('inicio')
		final_ferias = datetime.strptime(inicio_ferias, '%Y-%m-%d') + timedelta(days=int(request.POST.get('total_ferias'))) if not_none_not_empty(inicio_ferias) else None

		inicio_periodo = request.POST.get('inicio_periodo')
		final_periodo = request.POST.get('final_periodo')

		abono = int(request.POST.get('total_abono')) if not_none_not_empty(request.POST.get('total_abono')) else 0
		decimo = True if not_none_not_empty(request.POST.get('decimo')) else False

		observacao = request.POST.get('observacao')
		arquivos = request.FILES.getlist('arquivo')

		if not_none_not_empty(inicio_ferias, inicio_periodo, final_periodo, observacao):
			if Atividade.objects.filter(tipo=TipoAtividade.objects.get(slug='ferias'), autor=funcionario, data_finalizacao=None).exists():
				messages.warning(request, 'Você já possui férias em aberto!')
				return redirect('ferias')
			
			if SolicitacaoFerias.objects.filter(funcionario=funcionario).exclude(Q(status=SolicitacaoFerias.Status.APROVADO) | Q(status=SolicitacaoFerias.Status.RECUSADO)).exists():
				messages.warning(request, 'Você possui uma solicitação de férias em aberto!')
				return redirect('ferias')
			
			with transaction.atomic():
				solicitacao = SolicitacaoFerias.objects.create(
					funcionario=funcionario,
					aprovador=funcionario.gerente or ADMIN_USER,
					abono=abono,
					decimo=decimo,
					inicio_periodo=inicio_periodo,
					final_periodo=final_periodo,
					inicio_ferias=inicio_ferias,
					final_ferias=final_ferias,
					observacao=observacao,
				)

				if arquivos:
					for arquivo in arquivos:
						nome, documento = converter_documento(arquivo)

						if nome is None:
							messages.error(request, 'Os documentos devem ser do tipo JPG, PNG, GIF ou PDF!')
							return HttpResponseRedirect(request.META.get('HTTP_REFERER', '/'))

						DocumentosFerias(
							solicitacao=solicitacao,
							documento=documento,
							caminho=f'{nome}.pdf',
						).save()

				notify.send(
					sender=solicitacao.funcionario.usuario,
					recipient=solicitacao.aprovador.usuario,
					verb=f'Você possui uma nova solicitação de férias de {solicitacao.funcionario}',
				)

				send_mail(
					'Crony - Solicitação de Férias',
					f'Você possui uma nova solicitação de férias de {solicitacao.funcionario}',
					'avisos@novadigitalizacao.com.br',
					[solicitacao.aprovador.email],
					fail_silently=False,
				)
				
				add_coins(funcionario, 5, 'Solicitação de férias')
				messages.success(request, 'Solicitação enviada com sucesso!')
		
		elif not_none_not_empty(request.POST.get('pdf')):
			dados_empresa = {'nome': Variavel.objects.get(chave='NOME_EMPRESA').valor, 'cnpj': Variavel.objects.get(chave='CNPJ').valor, 'inscricao': Variavel.objects.get(chave='INSC_ESTADUAL').valor}
			filename = 'relatorio_ferias_funcionarios.pdf'
			context = {
				'autor': request.user.get_full_name,
				'ferias': ferias,
				'funcionarios': funcionarios,
				'dados_empresa': dados_empresa
			}
			return RenderToPDF(request, 'relatorios/ferias.html', context, filename).weasyprint()
		
		elif not_none_not_empty(request.POST.get('csv')):
			dataset = list()
			for funcionario, dados in ferias.items():
				for info in dados:
					dataset.append({
						'funcionario': funcionario,
						'ano_referencia': info['periodo'],
						'inicio_periodo': info['inicio'],
						'final_periodo': info['vencimento'],
						'saldo': info['saldo']
					})
			
			colunas = ['funcionario', 'ano_referencia', 'inicio_periodo', 'final_periodo', 'saldo']

			response = HttpResponse(content_type='text/csv')
			response['Content-Disposition'] = 'attachment; filename=ferias_funcionarios.csv'
			
			response.write(codecs.BOM_UTF8)

			df = pd.DataFrame(dataset, columns=colunas)
			df.to_csv(response, sep=';', index=False, encoding='utf-8')
			
			return response
		
		else:
			messages.warning(request, 'Preencha todos os campos obrigatórios!')
		
		return redirect('ferias')

	context.update({
		'ferias': ferias,
		'statuses': statuses,
		'minhas_ferias': ferias.get(funcionario, []),
		'solicitacoes': solicitacoes.order_by('-status'),
	})

	return render(request, 'pages/ferias.html', context)


# Page
@base_context_required
def DesempenhoView(request, context):
	funcionarios = context['funcionarios']
	funcionario = context['funcionario']

	# Filtros disponíveis na página
	tipos_filtrados = request.GET.getlist('tipos')
	status_filtrados = request.GET.getlist('status')
	funcionarios_filtrados = request.GET.getlist('funcionarios')

	tipos = TipoAtividade.objects.exclude(avaliativo=False)
	atividades = Atividade.objects.exclude(data_finalizacao=None).exclude(tipo__avaliativo=False)

	# Controle de acesso para usuário comum
	if request.user.get_access == 'common':
		funcionarios = funcionarios.filter(pk=funcionario.pk)
		atividades = atividades.filter(funcionarios__in=[funcionario.pk]).distinct()

	# Controle de acesso para usuário gerente
	if request.user.get_access == 'manager':
		funcionarios = funcionarios.filter(Q(gerente=funcionario) | Q(pk=funcionario.pk)).distinct()
		atividades = atividades.filter(Q(funcionarios__gerente=funcionario) | Q(funcionarios__in=[funcionario.pk])).distinct()

	# Aplicando o filtro para os funcionarios selecionados no cliente
	if funcionarios_filtrados:
		atividades = atividades.filter(funcionarios__in=[int(i) for i in funcionarios_filtrados]).distinct()

	avaliacoes = list()
	for atividade in atividades:
		dicionario = {
			'atvId': atividade.id,
			'avcId': None,
			'titulo': atividade.titulo,
			'descricao': atividade.descricao,
			'tipoId': atividade.tipo.id,
			'tipo': atividade.tipo.tipo,
			'inicio': atividade.inicio.strftime('%d/%m/%Y'),
			'final': atividade.final.strftime('%d/%m/%Y'),
			'funcionarios': [funcionario.nome_completo for funcionario in atividade.funcionarios.all()],
			'tempo': timezone.localtime() - atividade.data_finalizacao,
			'status': 0,
			'potencial': None,
			'desempenho': None,
			'avaliador': None,
			'observacao': None,
		}

		if Avaliacao.objects.filter(atividade=atividade).exists():
			avaliacao = Avaliacao.objects.filter(atividade=atividade).first()
			dicionario['avcId'] = avaliacao.id
			dicionario['status'] = 1
			dicionario['potencial'] = [i[1] for i in Avaliacao.Potencial.choices if avaliacao.potencial == i[0]][0]
			dicionario['potencial_id'] = [i[0] for i in Avaliacao.Potencial.choices if avaliacao.potencial == i[0]][0]
			dicionario['desempenho'] = [i[1] for i in Avaliacao.Desempenho.choices if avaliacao.desempenho == i[0]][0]
			dicionario['desempenho_id'] = [i[0] for i in Avaliacao.Desempenho.choices if avaliacao.desempenho == i[0]][0]
			dicionario['avaliador'] = avaliacao.avaliador
			dicionario['observacao'] = avaliacao.observacao
			avaliacoes.append(dicionario)
		else:
			avaliacoes.append(dicionario)

	# Aplicando o filtro para os status selecionados no cliente
	if status_filtrados:
		avaliacoes = list(filter(lambda d: d['status'] in [int(i) for i in status_filtrados], avaliacoes))
	else:
		avaliacoes = list(filter(lambda d: d['status'] == 0, avaliacoes))

	# Aplicando o filtro para os tipos de atividade selecionados no cliente
	if tipos_filtrados:
		avaliacoes = list(filter(lambda d: d['tipoId'] in [int(i) for i in tipos_filtrados], avaliacoes))

	context.update({
		'funcionarios': funcionarios,
		'tipos': tipos,
		'avaliacoes': avaliacoes,
	})

	return render(request, 'pages/desempenho.html', context)


# Modal
@login_required(login_url='entrar')
def AdicionarAvaliacaoView(request, atvid):
	if not request.method == 'POST':
		messages.warning(request, 'Método não permitido!')
		return redirect('inicio')

	atividade = Atividade.objects.get(pk=atvid)
	desempenho = int(request.POST.get('desempenho'))
	potencial = int(request.POST.get('potencial'))
	observacao = request.POST.get('observacao')

	if not_none_not_empty(desempenho, potencial, observacao):
		try:
			with transaction.atomic():
				Avaliacao(
					atividade=atividade,
					desempenho=desempenho,
					potencial=potencial,
					observacao=observacao,
					avaliador=Funcionario.objects.get(usuario=request.user),
				).save()

				for funcionario in atividade.funcionarios.all():
					add_coins(funcionario, 100, 'Receber avaliacação')

			messages.success(request, 'Avaliação foi criada com sucesso!')

		except Exception as e:
			messages.error(request, f'Avaliação não foi criada! {e}')

	else:
		messages.error(request, 'Preencha todos os campos!')

	return HttpResponseRedirect(request.META.get('HTTP_REFERER', '/'))
