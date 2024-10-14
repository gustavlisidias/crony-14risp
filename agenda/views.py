import codecs
import pandas as pd

from datetime import datetime, timedelta

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.db.models import Q
from django.http import HttpResponseRedirect, HttpResponse
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
from notifications.models import Notification
from ponto.renderers import RenderToPDF
from web.utils import not_none_not_empty, add_coins


# Page
@login_required(login_url='entrar')
def AgendaView(request):
	funcionarios = Funcionario.objects.filter(data_demissao=None).order_by('nome_completo')
	colaboradores = funcionarios
	funcionario = funcionarios.get(usuario=request.user)
	notificacoes = Notification.objects.filter(recipient=request.user, unread=True)
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

	context = {
		'funcionarios': funcionarios,
		'funcionario': funcionario,
		'notificacoes': notificacoes,
		'atividades': atividades,
		'listagem': listagem,
		'tipos': tipos,
		'colaboradores': colaboradores
	}
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

			add_coins(Funcionario.objects.get(usuario=request.user), 10)
			messages.success(request, 'Atividade criada com sucesso!')

		except Exception as e:
			messages.error(request, f'Atividade não foi criada! {e}')

	else:
		messages.error(request, 'Preencha todos os campos!')

	return HttpResponseRedirect(request.META.get('HTTP_REFERER', '/'))


# Page
@login_required(login_url='entrar')
def FeriasView(request):
	funcionarios = Funcionario.objects.filter(data_demissao=None).order_by('nome_completo')
	funcionario = funcionarios.get(usuario=request.user)
	notificacoes = Notification.objects.filter(recipient=request.user, unread=True)

	if request.user.get_access == 'admin':
		ferias = ferias_funcionarios(funcionarios)
	else:
		ferias = ferias_funcionarios(funcionarios.filter(pk=funcionario.pk))

	if funcionario.usuario.get_access == 'common':
		solicitacoes = SolicitacaoFerias.objects.filter(funcionario=funcionario, status=False)
	
	elif funcionario.usuario.get_access == 'manager':
		solicitacoes = SolicitacaoFerias.objects.filter(Q(funcionario=funcionario) | Q(aprovador=funcionario), status=False)

	else:
		solicitacoes = SolicitacaoFerias.objects.filter(status=False)

	if request.method == 'POST':
		inicio_ferias = request.POST.get('inicio')
		dias_ferias = request.POST.get('total_ferias')
		observacao = request.POST.get('observacao')
		arquivos = request.FILES.getlist('arquivo')
		admin = Funcionario.objects.filter(data_demissao=None, matricula__in=[i.strip() for i in Variavel.objects.get(chave='RESP_USERS').valor.split(',')]).first()

		if not_none_not_empty(inicio_ferias, dias_ferias, observacao):
			atividade_aberta = Atividade.objects.filter(tipo=TipoAtividade.objects.get(slug='ferias'), autor=funcionario, data_finalizacao=None).exists()
			solicitacao_aberta = SolicitacaoFerias.objects.filter(funcionario=funcionario, status=False).exists()
			if atividade_aberta or solicitacao_aberta:
				messages.warning(request, 'Você já possui férias em aberto!')
				return redirect('ferias')

			final_ferias = datetime.strptime(inicio_ferias, '%Y-%m-%d') + timedelta(days=int(dias_ferias))
			with transaction.atomic():
				solicitacao = SolicitacaoFerias.objects.create(
					funcionario=funcionario,
					aprovador=funcionario.gerente or admin,
					abono=request.POST.get('total_abono') if not_none_not_empty(request.POST.get('total_abono')) else 0,
					decimo=True if not_none_not_empty(request.POST.get('decimo')) else False,
					inicio=inicio_ferias,
					final=final_ferias,
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
				
				add_coins(funcionario, 5)
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
			dataset = []
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

	context = {
		'funcionarios': funcionarios,
		'funcionario': funcionario,
		'notificacoes': notificacoes,
		'minhas_ferias': ferias.get(funcionario.nome_completo, []),
		'solicitacoes': solicitacoes,
	}
	return render(request, 'pages/ferias.html', context)


# Page
@login_required(login_url='entrar')
def DesempenhoView(request):
	# Filtros disponíveis na página
	tipos_filtrados = request.GET.getlist('tipos')
	status_filtrados = request.GET.getlist('status')
	funcionarios_filtrados = request.GET.getlist('funcionarios')

	funcionarios = Funcionario.objects.filter(data_demissao=None).order_by('nome_completo')
	funcionario = funcionarios.get(usuario=request.user)
	notificacoes = Notification.objects.filter(recipient=request.user, unread=True)
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

	avaliacoes = []
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

	context = {
		'funcionarios': funcionarios,
		'funcionario': funcionario,
		'notificacoes': notificacoes,
		'tipos': tipos,
		'avaliacoes': avaliacoes,
	}
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
					add_coins(funcionario, 100)

			messages.success(request, 'Avaliação foi criada com sucesso!')

		except Exception as e:
			messages.error(request, f'Avaliação não foi criada! {e}')

	else:
		messages.error(request, 'Preencha todos os campos!')

	return HttpResponseRedirect(request.META.get('HTTP_REFERER', '/'))
