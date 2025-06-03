import pytz
import os
import json

from datetime import datetime, date, timedelta
from collections import defaultdict

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.contenttypes.models import ContentType
from django.core.mail import send_mail
from django.db import transaction
from django.http import HttpResponseRedirect
from django.shortcuts import redirect, render, get_object_or_404
from django.utils.safestring import mark_safe

from agenda.models import Atividade
from avaliacoes.models import Avaliacao, Resposta as RespostaAvaliacao
from cursos.models import ProgressoEtapa
from funcionarios.models import Funcionario, Perfil, JornadaFuncionario
from pesquisa.models import Pesquisa, Resposta
from ponto.models import Ponto, Fechamento
from notifications.models import Notification
from notifications.signals import notify
from settings.settings import MEDIA_ROOT
from web.decorators import base_context_required
from web.models import Comentario, Humor, Postagem, Ouvidoria, MensagemOuvidoria, Celebracao, Moeda
from web.utils import not_none_not_empty, add_coins


ADMIN_USER = Funcionario.objects.get(pk=3)


# Page
@base_context_required
def InicioView(request, context):
	hoje = date.today()
	funcionarios = context['funcionarios']
	funcionario = context['funcionario']

	# Geral
	posts = Postagem.objects.all().order_by('-data_cadastro')
	comunicado = Notification.objects.filter(recipient=request.user, unread=True, level='communication').order_by('id').first()
	celebracoes = Celebracao.objects.filter(data_celebracao__range=[hoje - timedelta(days=2), hoje], funcionario__in=[funcionario.id]).order_by('id')

	# Informações para o sidebar direito
	atividades = Atividade.objects.filter(funcionarios=funcionario, data_finalizacao=None).values('titulo', 'inicio', 'final').order_by('inicio')
	perfil = Perfil.objects.get(funcionario=funcionario)
	ponto = Ponto.objects.filter(funcionario=funcionario).order_by('data', 'hora').last()
	moedas = sum([i.pontuacao for i in Moeda.objects.filter(funcionario=funcionario, data_cadastro__date__month=hoje.month, data_cadastro__date__year=hoje.year)])

	# Coleta de informações sobre humor
	humor = Humor.objects.filter(funcionario=funcionario, data_cadastro__date=hoje)
	weekday = 1 if hoje.weekday() + 2 == 8 else hoje.weekday() + 2
	final_jornada = datetime.combine(hoje, JornadaFuncionario.objects.filter(funcionario=funcionario, final_vigencia=None, dia=weekday).order_by('hora').last().hora)

	# Pendências do colaborador
	pesquisas_pendentes = False
	for pesquisa in Pesquisa.objects.filter(funcionarios=funcionario, data_encerramento__gte=datetime.now().replace(tzinfo=pytz.utc)):
		if not Resposta.objects.filter(funcionario=funcionario, pergunta__pesquisa=pesquisa):
			pesquisas_pendentes = True

	avaliacoes_pendentes = False
	for av in Avaliacao.objects.filter(avaliadores=funcionario):
		if not RespostaAvaliacao.objects.filter(referencia__avaliacao=av, funcionario=funcionario).exists():
			avaliacoes_pendentes = True
	
	pendencias = {
		'pesquisas': pesquisas_pendentes,
		'perfil': not_none_not_empty(funcionario.nome_mae, funcionario.nome_pai, funcionario.rg, funcionario.data_expedicao, funcionario.rua, funcionario.numero, funcionario.cep) is False,
		'cursos': ProgressoEtapa.objects.filter(funcionario=funcionario, data_conclusao=None).exists(),
		'avaliacoes': avaliacoes_pendentes,
		'humor': final_jornada - timedelta(hours=1) <= datetime.now() <= final_jornada + timedelta(hours=1) and not humor.exists()
	}

	# Configuração da paginação
	maximo_publicacao = 3
	contador_publicacao = int(request.GET.get('page', 0)) + maximo_publicacao

	if len(posts) <= maximo_publicacao or contador_publicacao > len(posts):
		paginacao = {'status': False, 'count': len(posts)}
	else:
		paginacao = {'status': True, 'count': contador_publicacao}
		posts = posts[:contador_publicacao]

	for post in posts:
		post.curtidas_funcionarios = list(post.curtidas.values_list('funcionario__id', flat=True))

	for celebracao in celebracoes:
		celebracao.curtidas_funcionarios = list(celebracao.curtidas.values_list('funcionario__id', flat=True))

	if request.method == 'POST':
		if not_none_not_empty(request.POST.get('mood')) and not humor:
			try:
				observacao = request.POST.get('mood_observacao')
				humor_choice = [i for i in Humor.Status.choices if i[0] == request.POST.get('mood')][0]

				Humor(humor=str(humor_choice[0]), funcionario=funcionario, observacao=observacao).save()
				add_coins(funcionario, 10, 'Resposta afetivograma')
				
				descricao = observacao if not_none_not_empty(observacao) else f'Atenção ao {funcionario.nome_completo}, está com o humor {humor_choice[1]}!'

				if int(humor_choice[0]) <= 2:
					notify.send(
						sender=funcionario.usuario,
						recipient=ADMIN_USER.usuario,
						verb='Foi enviado um humor negativo',
						description=descricao
					)
				
				if int(humor_choice[0]) == 1:
					send_mail(
						'Foi enviado um humor negativo',
						descricao,
						'avisos@novadigitalizacao.com.br',
						['anderson@novadigitalizacao.com.br'],
						fail_silently=False,
					)
				
				messages.success(request, 'Obrigado por nos enviar seu humor!')

			except Exception as e:
				messages.error(request, f'Oops, ocorreu um erro ao enviar: {e}')

			return redirect('inicio')

	context.update({
		'paginacao': paginacao,
		'posts': posts,
		'funcionarios': funcionarios,
		'funcionario': funcionario,
		'comunicado': comunicado,
		'celebracoes': celebracoes,
		'atividades': atividades,
		'perfil': perfil,
		'ponto': datetime.combine(ponto.data, ponto.hora) if ponto else None,
		'pendencias': pendencias,
		'moedas': moedas
	})
	
	return render(request, 'pages/inicio.html', context)


# Modal
@login_required(login_url='entrar')
def AdicionarPostView(request):
	if not request.method == 'POST':
		messages.warning(request, 'Método não permitido!')
		return redirect('inicio')

	titulo = request.POST.get('titulo')
	texto = request.POST.get('texto')

	if not_none_not_empty(titulo, texto):
		try:
			funcionario = Funcionario.objects.get(usuario=request.user)
			Postagem(titulo=titulo, texto=texto, funcionario=funcionario).save()

			for i in Funcionario.objects.filter(data_demissao=None):
				if i.get_tag in texto:
					notify.send(
						sender=request.user,
						recipient=i.usuario,
						verb='Você foi marcado em uma nova postagem!'
					)

			add_coins(funcionario, 5, 'Criar postagem')
			messages.success(request, 'Postagem criada com sucesso!')

		except Exception as e:
			messages.error(request, f'Postagem não foi criada! {e}')

	else:
		messages.error(request, 'Preencha todos os campos!')

	return redirect('inicio')


# Modal
@login_required(login_url='entrar')
def AdicionarCelebracaoView(request):
	if not request.method == 'POST':
		messages.warning(request, 'Método não permitido!')
		return redirect('inicio')
	
	celebrante = Funcionario.objects.get(usuario=request.user) if request.user.get_access != 'admin' else None
	if request.user.get_access != 'admin' and Celebracao.objects.filter(data_celebracao=date.today(), celebrante=celebrante).exists():
		messages.warning(request, 'Você já realizou uma celebração hoje!')
		return redirect('inicio') 
	
	titulo = request.POST.get('titulo')
	texto = request.POST.get('texto')
	data = request.POST.get('data')
	funcionarios = request.POST.getlist('funcionarios')

	if not_none_not_empty(titulo, texto, data, funcionarios):
		try:
			celebracao = Celebracao.objects.create(titulo=titulo, texto=texto, data_celebracao=data, celebrante=celebrante)
			celebracao.funcionario.set(funcionarios)
			celebracao.save()

			for i in Funcionario.objects.filter(data_demissao=None):
				if i.get_tag in texto:
					notify.send(
						sender=request.user,
						recipient=i.usuario,
						verb='Você foi marcado em uma nova celebração!'
					)

			messages.success(request, 'Celebração salva com sucesso!')

		except Exception as e:
			messages.error(request, f'Celebração não foi salva: {e}!')
	else:
		messages.error(request, 'Preencha todos os campos obrigatórios!')
	
	return redirect('inicio')


# Modal
@login_required(login_url='entrar')
def EditarPostView(request, post):
	if not request.method == 'POST':
		messages.warning(request, 'Método não permitido!')
		return redirect('inicio')

	titulo = request.POST.get('titulo')
	texto = request.POST.get('texto')

	if not_none_not_empty(titulo, texto):
		try:
			postagem = Postagem.objects.get(pk=post)
			postagem.titulo = titulo
			postagem.texto = texto
			postagem.save()

			for i in Funcionario.objects.filter(data_demissao=None):
				if i.get_tag in texto:
					notify.send(
						sender=request.user,
						recipient=i.usuario,
						verb='Você foi marcado em uma nova postagem!'
					)

			messages.success(request, 'Postagem alterada com sucesso!')

		except Exception as e:
			messages.error(request, f'Postagem não foi alterada! {e}')

	else:
		messages.error(request, 'Preencha todos os campos!')

	return redirect('inicio')


# Modal
@login_required(login_url='entrar')
def ExcluirPostView(request, post):
	if not request.method == 'POST':
		messages.warning(request, 'Método não permitido!')
		return redirect('inicio')

	try:
		Postagem.objects.get(pk=post).delete()
		messages.success(request, 'Postagem excluida com sucesso!')

	except Exception as e:
		messages.error(request, f'Postagem não foi excluida! {e}')

	return redirect('inicio')


# Modal
@login_required(login_url='entrar')
def ComentarPostView(request, post, modelo):
	if not request.method == 'POST':
		messages.warning(request, 'Método não permitido!')
		return redirect('inicio')
	
	if modelo == 'postagem':
		model = Postagem
		value = 0
	elif modelo == 'celebracao':
		model = Celebracao
		value = 5

	obj = get_object_or_404(model, pk=post)
	content_type = ContentType.objects.get_for_model(model)
	funcionario = get_object_or_404(Funcionario, usuario=request.user)

	comentario = request.POST.get('comentario')

	if not_none_not_empty(comentario):
		try:
			Comentario(content_type=content_type, object_id=obj.id, funcionario=funcionario, comentario=comentario).save()
			add_coins(funcionario, value, 'Comentar postagem ou publicação')

			if request.user != obj.funcionario.usuario:
				notify.send(
					sender=funcionario.usuario,
					recipient=obj.funcionario.usuario,
					verb='Você tem um novo comentário',
				)

			messages.success(request, 'Comentario criado com sucesso!')

		except Exception as e:
			messages.error(request, f'Comentario não foi criado! {e}')

	else:
		messages.error(request, 'Preencha todos os campos!')

	return redirect('inicio')


# Modal
@login_required(login_url='entrar')
def EditarComentarioView(request, comment):
	if not request.method == 'POST':
		messages.warning(request, 'Método não permitido!')
		return redirect('inicio')

	comentario = request.POST.get('comentario')

	if not_none_not_empty(comentario):
		try:
			Comentario.objects.filter(pk=comment).update(comentario=comentario)
			messages.success(request, 'Comentario alterado com sucesso!')

		except Exception as e:
			messages.error(request, f'Comentario não foi alterado! {e}')

	else:
		messages.error(request, 'Preencha todos os campos!')

	return redirect('inicio')


# Modal
@login_required(login_url='entrar')
def ExcluirComentarioView(request, comment):
	if not request.method == 'POST':
		messages.warning(request, 'Método não permitido!')
		return redirect('inicio')

	try:
		Comentario.objects.get(pk=comment).delete()
		messages.success(request, 'Comentario excluido com sucesso!')

	except Exception as e:
		messages.error(request, f'Comentario não foi excluido! {e}')

	return redirect('inicio')


# Page
@base_context_required
def OuvidoriaView(request, context):
	funcionarios = context['funcionarios']
	funcionario = context['funcionario']

	tickets = Ouvidoria.objects.all()

	if not request.user.is_ouvidor:
		funcionarios = funcionarios.filter(pk=funcionario.pk)
		tickets = tickets.filter(funcionario=funcionario)

	context.update({
		'funcionarios': funcionarios,
		'tickets': tickets,
		'categorias': [{'id': i[0], 'title': i[1]} for i in Ouvidoria.Categoria.choices]
	})

	return render(request, 'pages/ouvidoria.html', context)


# Modal
@login_required(login_url='entrar')
def AdicionarOuvidoriaView(request):
	if not request.method == 'POST':
		messages.warning(request, 'Método não permitido!')
		return redirect('inicio')

	try:
		with transaction.atomic():
			categoria = [i for i in Ouvidoria.Categoria.choices if i[0] == int(request.POST.get('categoria'))][0]
			funcionario = Funcionario.objects.get(usuario=request.user)
			ouvidor = Funcionario.objects.filter(data_demissao=None, usuario__is_ouvidor=True).first()

			ouvidoria = Ouvidoria.objects.create(
				funcionario=funcionario,
				responsavel=ouvidor,
				categoria=categoria[0],
				assunto=request.POST.get('assunto'),
				descricao=request.POST.get('descricao'),
				anonimo=True if not_none_not_empty(request.POST.get('anonimo')) else False,
			)

			MensagemOuvidoria(
				ticket=ouvidoria,
				remetente=Funcionario.objects.get(usuario=request.user),
				mensagem=request.POST.get('descricao')
			).save()

			add_coins(funcionario, 30, 'Enviar ouvidoria')
			
			notify.send(
				sender=request.user,
				recipient=ouvidor.usuario,
				verb=f'Uma manifestação foi aberta {ouvidoria.assunto} ({categoria[1]})',
			)

		messages.success(request, 'Manifestação enviada com sucesso!')

	except Exception as e:
		messages.error(request, f'Manifestação não foi salva! {e}')

	return redirect('ouvidoria')


# Page
@base_context_required
def RankingView(request, context):
	hoje = date.today()
	moedas_abertas = Moeda.objects.filter(funcionario__visivel=True, data_cadastro__date__month=hoje.month, data_cadastro__date__year=hoje.year).order_by('-pontuacao')
	moedas_fechadas = Moeda.objects.filter(funcionario__visivel=True).exclude(pk__in=[i.pk for i in moedas_abertas]).order_by('-pontuacao')

	score_abertas, score_fechadas = defaultdict(lambda: defaultdict(int)), defaultdict(lambda: defaultdict(int))
	for moeda in moedas_abertas:
		referencia = moeda.data_cadastro.strftime('%Y%m')
		score_abertas[moeda.funcionario][referencia] += moeda.pontuacao
	
	for moeda in moedas_fechadas:
		referencia = moeda.data_cadastro.strftime('%Y%m')
		score_fechadas[moeda.funcionario][referencia] += moeda.pontuacao

	lista_score_abertas = sorted(
        [{'funcionario': func, 'referencia': ref, 'pontuacao': pontos}
         for func, refs in score_abertas.items() for ref, pontos in refs.items()],
        key=lambda x: x['pontuacao'], reverse=True
    )

	lista_score_fechadas = sorted(
        [{'funcionario': func, 'referencia': ref, 'pontuacao': pontos}
         for func, refs in score_fechadas.items() for ref, pontos in refs.items()],
        key=lambda x: (x['referencia'], x['pontuacao']), reverse=True
    )

	top = list()
	if len(lista_score_abertas) >= 3:
		top.append(lista_score_abertas[:3])

	context.update({
		'pontuacoes_atuais': lista_score_abertas,
		'pontuacoes_fechadas': lista_score_fechadas,
		'top': top,
	})

	return render(request, 'pages/ranking.html', context)


# Modal
@login_required(login_url='entrar')
def AdicionarMoedaView(request, fecid):
	if not request.method == 'POST':
		messages.warning(request, 'Método não permitido!')
		return redirect('pontos')
	
	try:
		fechamento = Fechamento.objects.get(pk=fecid)
		fechamento.moedas += int(request.POST.get('quantidade'))
		fechamento.save()
		messages.success(request, 'Moedas inseridas com sucesso')

	except Exception as e:
		messages.error(request, f'Moedas não foram inseridas! {e}')

	return HttpResponseRedirect(request.META.get('HTTP_REFERER', '/'))
