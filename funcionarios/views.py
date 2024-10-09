import os
import json
import math
import pytz
import subprocess
import tempfile

from django.contrib import messages
from django.contrib.auth import update_session_auth_hash
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import PasswordChangeForm
from django.db.models import Count, Q
from django.http import JsonResponse, HttpResponseRedirect
from django.shortcuts import redirect, render
from django.utils import timezone

from datetime import datetime, timedelta
from slugify import slugify

from agenda.models import Atividade, Avaliacao
from cities_light.models import Region as Estado
from cities_light.models import SubRegion as Cidade
from configuracoes.models import Contrato, Jornada, Variavel
from notifications.signals import notify
from funcionarios.models import (
	Cargo,
	Documento,
	Funcionario,
	HistoricoFuncionario,
	JornadaFuncionario,
	Perfil,
	Score,
	Setor,
	TipoDocumento,
	Feedback,
	SolicitacaoFeedback,
	RespostaFeedback
)
from funcionarios.utils import obter_arvore, cadastro_funcionario, atualizar_perfil_funcionario
from ponto.models import Ponto
from ponto.renderers import RenderToPDF
from ponto.utils import pontos_por_dia
from notifications.models import Notification
from settings.settings import BASE_DIR
from web.models import Humor
from web.utils import not_none_not_empty, add_coins


# Page
@login_required(login_url='entrar')
def FuncionariosView(request):
	funcionarios = Funcionario.objects.all().order_by('-data_demissao', 'nome_completo')
	funcionario = funcionarios.get(usuario=request.user)
	notificacoes = Notification.objects.filter(recipient=request.user, unread=True)

	if request.user.get_access != "admin":
		funcionarios = funcionarios.filter(data_demissao=None)

	setores = Setor.objects.all().order_by('setor')
	cargos = Cargo.objects.all().order_by('cargo')
	estados = Estado.objects.all().order_by('name')
	cidades = Cidade.objects.all().order_by('name')
	contratos = Contrato.objects.all().order_by('titulo')
	civis = [{'id': i[0], 'nome': i[1]} for i in Funcionario.Estados.choices]

	context = {
		'funcionarios': funcionarios,
		'funcionario': funcionario,
		'notificacoes': notificacoes,
		'setores': setores,
		'cargos': cargos,
		'estados': estados,
		'cidades': cidades,
		'contratos': contratos,
		'civis': civis
	}
	return render(request, 'pages/funcionarios.html', context)


# Modal
@login_required(login_url='entrar')
def AdicionarFuncionarioView(request):
	if request.user.get_access == 'common':
		messages.warning(request, 'Você não possui acesso para realizar essa ação!')
		return redirect('funcionarios')

	if not request.method == 'POST':
		messages.warning(request, 'Método não permitido!')
		return redirect('funcionarios')
	
	cadastro_funcionario(request)

	return redirect('funcionarios')


# Page
@login_required(login_url='entrar')
def EditarFuncionarioView(request, func):
	funcionarios = Funcionario.objects.filter().order_by('nome_completo')
	funcionario = funcionarios.get(usuario=request.user)
	colaborador = funcionarios.get(pk=func)
	notificacoes = Notification.objects.filter(recipient=request.user, unread=True)

	if request.user.get_access == 'common' and funcionario.usuario != request.user:
		messages.warning(request, 'Você não possui acesso para realizar essa ação!')
		return redirect('funcionarios')
	
	filtro_data_inicial = request.GET.get('data_inicial') if not_none_not_empty(request.GET.get('data_inicial')) else '2000-01-01' # (timezone.localdate() - timedelta(days=10)).strftime('%Y-%m-%d')
	filtro_data_final = request.GET.get('data_final') if not_none_not_empty(request.GET.get('data_final')) else timezone.localdate().strftime('%Y-%m-%d')
	filtro_nome = request.GET.get('nome')
	filtro_tipo = request.GET.getlist('tipo')

	setores = Setor.objects.all().order_by('setor')
	cargos = Cargo.objects.all().order_by('cargo')
	estados = Estado.objects.all().order_by('name')
	cidades = Cidade.objects.all().order_by('name')

	atividades = Atividade.objects.filter(funcionarios=colaborador, data_finalizacao=None).order_by('inicio')
	tipos = TipoDocumento.objects.all()

	documentos = Documento.objects.filter(funcionario=colaborador, data_documento__gte=filtro_data_inicial, data_documento__lte=filtro_data_final, tipo__in=tipos).order_by('-data_documento')
	humor = list(Humor.objects.filter(funcionario=colaborador).values('humor').annotate(contagem=Count('humor')))
	civis = [{'id': i[0], 'nome': i[1]} for i in Funcionario.Estados.choices]
	contratos = Contrato.objects.all()
	jornadas = JornadaFuncionario.objects.filter(funcionario=colaborador).order_by('funcionario__id', 'dia', 'ordem')
	
	avaliacoes = Avaliacao.objects.filter(atividade__funcionarios__in=[colaborador])
	if avaliacoes:
		avaliacao = {
			'desempenho': round(sum(i.desempenho for i in avaliacoes) / len(avaliacoes)), 
			'potencial': round(sum(i.potencial for i in avaliacoes) / len(avaliacoes)), 
		}
	else:
		avaliacao = {'desempenho': None, 'potencial': None}

	if not_none_not_empty(filtro_nome):
		documentos = documentos.filter(caminho__contains=filtro_nome)
	
	if not_none_not_empty(filtro_tipo):
		documentos = documentos.filter(tipo__in=[int(i) for i in filtro_tipo])

	if humor:
		for item in humor:
			item['humor'] = dict(Humor.Status.choices)[item['humor']]
	
	jornada = {}
	for item in jornadas.order_by('dia', 'hora'):
		if item.dia not in jornada:
			jornada[item.dia] = []
		jornada[item.dia].append({'tipo': item.get_tipo_display(), 'hora': item.hora, 'contrato': item.contrato})

	registros = Ponto.objects.filter(funcionario=colaborador).order_by('data', 'hora')
	if registros:
		pontos, scores = pontos_por_dia(registros.first().data, registros.last().data, colaborador)
	else:
		pontos, scores = None, None
	
	graph = {'total': timedelta(seconds=0), 'saldo': timedelta(seconds=0), 'banco': timedelta(seconds=0), 'scores': None}
	if pontos:
		graph['scores'] = list(scores.values())[0]
		for _, dados in pontos.items():
			for dado in dados:
				graph['total'] += dado['total']
				graph['saldo'] += dado['saldo']
				graph['banco'] += dado['banco']

	if request.method == 'POST':
		if request.user.get_access == 'common':
			messages.warning(request, 'Você não possui acesso para realizar essa ação!')
			return redirect('editar-funcionario', colaborador.id)
		
		# Atualização de dados pessoais do funcionário
		if not_none_not_empty(request.POST.get('nome_completo')):
			cadastro_funcionario(request, colaborador, True)

		# Atualização das informações/observações do funcionário
		if not_none_not_empty(request.POST.get('observacao')):
			try:
				colaborador.observacoes = request.POST.get('observacao')
				colaborador.save()
				messages.success(request, 'Informações adicionadas com sucesso!')
			except Exception as e:
				messages.error(request, f'Informações não foram adicionadas com sucesso: {e}')

		# Atualização de horários da jornada de trabalho do funcionário
		if not_none_not_empty(request.POST.get('contrato')):
			jornada_funcionario = JornadaFuncionario.objects.filter(funcionario=colaborador).order_by('funcionario__id', 'dia', 'ordem')
			contrato = Contrato.objects.get(pk=request.POST.get('contrato'))

			if not jornada_funcionario or jornada_funcionario.first().contrato != contrato:
				if (not jornada_funcionario.first().contrato.titulo.lower().startswith('clt')) and contrato.titulo.lower().startswith('clt'):
					add_coins(colaborador, 350)

				if jornada_funcionario:
					jornada_funcionario.delete()
				
				for horario in Jornada.objects.filter(contrato=contrato).order_by('contrato__id', 'dia', 'ordem'):
					JornadaFuncionario.objects.create(
						funcionario=colaborador,
						contrato=horario.contrato,
						tipo=horario.tipo,
						dia=horario.dia,
						hora=horario.hora,
						ordem=horario.ordem
					)

				messages.success(request, 'Horários alterados conforme novo contrato!')
				
			else:
				jornada_funcionario.delete()
				for dia, horarios in json.loads(request.POST.get('dados')).items():
					for index, (tipo, hora) in enumerate(horarios.items()):
						JornadaFuncionario(
							funcionario=colaborador,
							contrato=contrato,
							tipo=tipo[0].upper(),
							hora=datetime.strptime(hora, '%H:%M').time(),
							dia=dia,
							ordem=(index + 1)
						).save()

				messages.success(request, 'Horários atualizados com sucesso!')
			
			# Resetar score do funcionario
			if pontos:
				for obj in Score.objects.filter(funcionario=colaborador, fechado=False):
					obj.fechado = True
					obj.pontuacao = list(scores.values())[0][0]
					obj.save()
					
				Score(funcionario=colaborador).save()
		
		# Exportar histórico do funcionário
		if not_none_not_empty(request.POST.get('historico')):
			dados = HistoricoFuncionario.objects.filter(funcionario=colaborador).order_by('-data_alteracao')
			filename = f'historico-{slugify(colaborador.nome_completo.lower())}.pdf'
			dados_empresa = {'nome': Variavel.objects.get(chave='NOME_EMPRESA').valor, 'cnpj': Variavel.objects.get(chave='CNPJ').valor, 'inscricao': Variavel.objects.get(chave='INSC_ESTADUAL').valor}
			context = {
				'dados': dados,
				'funcionario': colaborador,
				'contrato': JornadaFuncionario.objects.filter(funcionario=colaborador).first().contrato,
				'autor': Funcionario.objects.get(usuario=request.user),
				'hoje': datetime.now().replace(tzinfo=pytz.utc),
				'dados_empresa': dados_empresa
			}
			return RenderToPDF(request, 'relatorios/historico.html', context, filename).weasyprint()

		return redirect('editar-funcionario', colaborador.id)
	
	context = {
		'funcionarios': funcionarios,
		'funcionario': funcionario,
		'colaborador': colaborador,
		'notificacoes': notificacoes,

		'setores': setores,
		'cargos': cargos,
		'estados': estados,
		'cidades': cidades,

		'atividades': atividades,
		'documentos': documentos,
		'tipos': tipos,
		'humor': humor,
		'civis': civis,

		'avaliacao': avaliacao,
		'contratos': contratos,
		'contrato': jornadas.first().contrato,

		'jornada': jornada,
		'pontos': pontos,
		'graph': graph,

		'filtros': {'inicio': filtro_data_inicial, 'final': filtro_data_final, 'nome': filtro_nome, 'tipo': filtro_tipo },
	}
	return render(request, 'pages/funcionario.html', context)


# Page
@login_required(login_url='entrar')
def PerfilFuncionarioView(request):
	funcionario = Funcionario.objects.get(usuario=request.user)
	notificacoes = Notification.objects.filter(recipient=request.user, unread=True)
	perfil = Perfil.objects.get(funcionario=funcionario)

	estados = Estado.objects.all().order_by('name')
	cidades = Cidade.objects.all().order_by('name')
	civis = [{'key': i[0], 'value': i[1]} for i in Funcionario.Estados.choices]
	historico = HistoricoFuncionario.objects.filter(funcionario=funcionario).values('cargo__cargo', 'setor__setor').distinct()

	jornada = {}
	for item in JornadaFuncionario.objects.filter(funcionario=funcionario).order_by('funcionario__id', 'dia', 'ordem'):
		if item.dia not in jornada:
			jornada[item.dia] = []
		jornada[item.dia].append({'tipo': item.get_tipo_display(), 'hora': item.hora, 'contrato': item.contrato})

	if request.method == 'POST':
		if request.user.get_access == 'common':
			messages.warning(request, 'Você não possui acesso para realizar essa ação!')
			return redirect('perfil')

		if not_none_not_empty(request.POST.get('remover')):
			perfil.foto = None
			perfil.save()
			messages.success(request, 'Foto removida com sucesso!')
			return redirect('perfil')
		
		if request.FILES.get('foto'):
			perfil.foto = request.FILES.get('foto')
			add_coins(funcionario, 50)
			
		perfil.bio = request.POST.get('bio')
		perfil.save()

		atualizar_perfil_funcionario(request, funcionario)

		add_coins(funcionario, 5)

		admin = Funcionario.objects.filter(data_demissao=None, usuario__is_admin=True).first()
		notify.send(
			sender=request.user,
			recipient=admin.usuario,
			verb=f'Perfil do funcionário {funcionario.nome_completo} foi alterado!'
		)

		messages.success(request, 'Perfil alterado com sucesso!')
		return redirect('perfil')

	context = {
		'funcionario': funcionario,
		'notificacoes': notificacoes,
		'perfil': perfil,
		'jornada': jornada,
		'estados': estados,
		'cidades': cidades,
		'civis': civis,
		'historico': historico
	}
	return render(request, 'pages/perfil.html', context)


# Modal
@login_required(login_url='entrar')
def AlterarSenhaView(request):
	if not request.method == 'POST':
		messages.warning(request, 'Método não permitido!')
		return redirect('perfil')
	
	funcionario = Funcionario.objects.get(usuario=request.user)
	form = PasswordChangeForm(funcionario.usuario, request.POST)

	if form.is_valid():
		user = form.save()
		update_session_auth_hash(request, user)
		messages.success(request, 'Sua senha foi alterada com sucesso!')
		
	else:
		for field, errors in form.errors.items():
			for error in errors:
				messages.error(request, f'{field} - {error}')
	
	return redirect('perfil')
	

# Page
@login_required(login_url='entrar')
def DocumentosView(request):
	if request.user.get_access == 'common':
		messages.warning(request, 'Você não possui acesso para realizar essa ação!')
		return redirect('inicio')

	filtro_data_inicial = request.GET.get('data_inicial') if not_none_not_empty(request.GET.get('data_inicial')) else '2018-01-01' # (timezone.localdate() - timedelta(days=360)).strftime('%Y-%m-%d')
	filtro_data_final = request.GET.get('data_final') if not_none_not_empty(request.GET.get('data_final')) else timezone.localdate().strftime('%Y-%m-%d')
	filtro_nome = request.GET.get('nome')
	filtro_tipo = request.GET.getlist('tipo')

	funcionarios = Funcionario.objects.filter(data_demissao=None).order_by('nome_completo')
	funcionario = funcionarios.get(usuario=request.user)
	notificacoes = Notification.objects.filter(recipient=request.user, unread=True)

	tipos = TipoDocumento.objects.all()
	documentos = Documento.objects.filter(funcionario=None, data_documento__range=[filtro_data_inicial, filtro_data_final], tipo__in=tipos).order_by('-data_documento')
	
	if not_none_not_empty(filtro_nome):
		documentos = documentos.filter(caminho__contains=filtro_nome)
	
	if not_none_not_empty(filtro_tipo):
		documentos = documentos.filter(tipo__in=[int(i) for i in filtro_tipo])

	context = {
		'funcionarios': funcionarios,
		'funcionario': funcionario,
		'notificacoes': notificacoes,
		'documentos': documentos,
		'tipos': tipos,
		'filtros': {'inicio': filtro_data_inicial, 'final': filtro_data_final, 'nome': filtro_nome, 'tipo': filtro_tipo },
	}
	return render(request, 'pages/documentos.html', context)
	

# Page
@login_required(login_url='entrar')
def FeedbackView(request):
	funcionarios = Funcionario.objects.filter(data_demissao=None).order_by('nome_completo')
	funcionario = funcionarios.get(usuario=request.user)
	notificacoes = Notification.objects.filter(recipient=request.user, unread=True)

	solicitacoes = SolicitacaoFeedback.objects.filter(destinatario__usuario=request.user).order_by('-data_cadastro')
	feedbacks = Feedback.objects.all().order_by('-data_cadastro')
	feedbacks_enviados = feedbacks.filter(remetente=funcionario)
	feedbacks_recebidos = feedbacks.filter(destinatario=funcionario)
	modelos = [{'key': i[0], 'value': i[1]} for i in Feedback.Modelos.choices]

	for feedback in feedbacks:
		query = RespostaFeedback.objects.filter(feedback=feedback)
		feedback.resposta = query.first().resposta.strip() if query.exists() else None
		feedback.util = query.first().util if query.exists() else None

	for feedback in feedbacks_enviados:
		query = RespostaFeedback.objects.filter(feedback=feedback)
		feedback.resposta = query.first().resposta.strip() if query.exists() else None
		feedback.util = query.first().util if query.exists() else None
		
	for feedback in feedbacks_recebidos:
		query = RespostaFeedback.objects.filter(feedback=feedback)
		feedback.resposta = query.first().resposta.strip() if query.exists() else None
		feedback.util = query.first().util if query.exists() else None

	for solicitacao in solicitacoes:
		if Feedback.objects.filter(remetente=solicitacao.destinatario, destinatario=solicitacao.remetente, data_cadastro__gt=solicitacao.data_cadastro).exists():
			solicitacao.respondido = True
		else:
			solicitacao.respondido = False

	try:
		comprometimentos = feedbacks_recebidos.filter(comprometimento__gte=1)
		conhecimentos = feedbacks_recebidos.filter(conhecimento__gte=1)
		produtividades = feedbacks_recebidos.filter(produtividade__gte=1)
		comportamentos = feedbacks_recebidos.filter(comportamento__gte=1)
		notas = {
			'comprometimento': math.ceil(sum([i.comprometimento for i in comprometimentos]) / len(comprometimentos)),
			'conhecimento': math.ceil(sum([i.conhecimento for i in conhecimentos]) / len(conhecimentos)),
			'produtividade': math.ceil(sum([i.produtividade for i in produtividades]) / len(produtividades)),
			'comportamento': math.ceil(sum([i.comportamento for i in comportamentos]) / len(comportamentos))
		}
	except Exception:
		notas = {'comprometimento': 0, 'conhecimento': 0, 'produtividade': 0, 'comportamento': 0}

	context = {
		'funcionarios': funcionarios,
		'funcionario': funcionario,
		'notificacoes': notificacoes,
		'solicitacoes': solicitacoes,
		'feedbacks': feedbacks,
		'feedbacks_enviados': feedbacks_enviados,
		'feedbacks_recebidos': feedbacks_recebidos,
		'modelos': modelos,
		'notas': notas
	}
	return render(request, 'pages/feedback.html', context)


# Modal
@login_required(login_url='entrar')
def SolicitarFeedbackView(request):
	if not request.method == 'POST':
		messages.warning(request, 'Método não permitido!')
		return redirect('feedback')
	
	solicitacao = request.POST.get('solicitacao')
	remetente = Funcionario.objects.get(usuario=request.user)
	destinatario = Funcionario.objects.get(pk=int(request.POST.get('destinatario')))
	
	if not_none_not_empty(solicitacao):
		SolicitacaoFeedback(
			solicitacao=solicitacao,
			destinatario=destinatario,
			remetente=Funcionario.objects.get(usuario=request.user)
		).save()

		notify.send(
			sender=request.user,
			recipient=destinatario.usuario,
			verb=f'Você tem uma nova solicitação de feedback de {remetente.nome_completo}!',
			description=solicitacao
		)

		messages.success(request, 'Solicitação de Feedback enviada com sucesso!')

	else:
		messages.error(request, 'Insira todas as informações obrigatórias!')
	
	return redirect('feedback')


# Modal
@login_required(login_url='entrar')
def EnviarFeedbackView(request):
	if not request.method == 'POST':
		messages.warning(request, 'Método não permitido!')
		return redirect('feedback')
	
	modelo = request.POST.get('modelo')

	comprometimento = int(request.POST.get('comprometimento')) if not_none_not_empty(request.POST.get('comprometimento')) else 0
	conhecimento = int(request.POST.get('conhecimento')) if not_none_not_empty(request.POST.get('conhecimento')) else 0
	produtividade = int(request.POST.get('produtividade')) if not_none_not_empty(request.POST.get('produtividade')) else 0
	comportamento = int(request.POST.get('comportamento')) if not_none_not_empty(request.POST.get('comportamento')) else 0

	destinatario = Funcionario.objects.get(pk=int(request.POST.get('destinatario')))
	remetente = Funcionario.objects.get(usuario=request.user)
	mensagem = request.POST.get('mensagem')

	if not_none_not_empty(modelo, comprometimento, conhecimento, produtividade, comportamento, mensagem):
		Feedback(
			modelo=modelo,
			comprometimento=comprometimento,
			conhecimento=conhecimento,
			produtividade=produtividade,
			comportamento=comportamento,
			destinatario=destinatario,
			remetente=remetente,
			mensagem=mensagem,
			anonimo=False
		).save()

		notify.send(
			sender=request.user,
			recipient=destinatario.usuario,
			verb=f'Você tem um novo feedback de {remetente.nome_completo}!',
			description=mensagem
		)

		messages.success(request, 'Feedback enviado com sucesso!')

	else:
		messages.error(request, 'Insira todas as informações obrigatórias!')
		
	return redirect('feedback')


# Modal
@login_required(login_url='entrar')
def ResponderFeedbackView(request, feed):
	if not request.method == 'POST':
		messages.warning(request, 'Método não permitido!')
		return redirect('feedback')

	try:
		RespostaFeedback(
			feedback=Feedback.objects.get(pk=feed),
			resposta=request.POST.get('resposta'),
			util=True if request.POST.get('util') == 'sim' else False
		).save()

		messages.success(request, 'Resposta de feedback enviado com sucesso!')
	
	except Exception as e:
		messages.error(request, f'Resposta de feedback não foi enviado: {e}')

	return redirect('feedback')


# Modal
def ImportarDocumentosView(request):
	caminhos = [i.valor for i in Variavel.objects.filter(Q(chave='PATH_DOCS') | Q(chave='PATH_DOCS_EMP'))]
	arvores, nodes = [], []

	try:
		for caminho in caminhos:
			arvores.append(obter_arvore(caminho))

	except Exception as e:
		return JsonResponse({'message': f'Ocorreu um erro ao ler os diretórios {caminhos}: {e}'}, status=500)

	if request.method == 'GET':
		return JsonResponse(arvores, safe=False, status=200)
	
	if request.method == 'POST':
		if request.POST.get('selected'):
			nodes = list(filter(None, request.POST.get('nodes').split(',')))

			with tempfile.NamedTemporaryFile(mode='w', delete=False) as temp_file:
				json.dump(nodes, temp_file)
				temp_file_path = temp_file.name 

			command = ['python', str(os.path.join(BASE_DIR, 'tasks', 'importador_documentos.py')), '--nodes', temp_file_path]
			subprocess.Popen(command, shell=True)

		if request.POST.get('all'):
			command = ['python', str(os.path.join(BASE_DIR, 'tasks', 'importador_documentos.py'))]
			subprocess.Popen(command, shell=True)

		messages.success(request, 'Importação de documentos iniciada!')
		return HttpResponseRedirect(request.META.get('HTTP_REFERER', '/'))