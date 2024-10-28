import pytz

from datetime import datetime, date

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.contenttypes.models import ContentType
from django.db import transaction
from django.http import HttpResponseRedirect
from django.shortcuts import redirect, render, get_object_or_404
from django.utils import timezone

from agenda.models import Atividade, TipoAtividade
from cursos.models import ProgressoEtapa
from configuracoes.models import Variavel
from funcionarios.models import Funcionario, Perfil
from pesquisa.models import Pesquisa, Resposta
from ponto.models import Ponto
from notifications.models import Notification
from notifications.signals import notify
from web.models import Comentario, Humor, Postagem, Ouvidoria, MensagemOuvidoria, Celebracao, Sugestao, Moeda
from web.utils import not_none_not_empty, add_coins


# Page
@login_required(login_url='entrar')
def InicioView(request):
	maximo_publicacao = 2
	contador_publicacao = int(request.GET.get('page')) + maximo_publicacao if request.GET.get('page') else maximo_publicacao
	hoje = timezone.localdate().strftime('%Y-%m-%d')

	posts = Postagem.objects.all().order_by('-data_cadastro')
	funcionarios = Funcionario.objects.filter(data_demissao=None).order_by('nome_completo')
	funcionario = funcionarios.get(usuario=request.user)
	notificacoes = Notification.objects.filter(recipient=request.user, unread=True)
	comunicado = Notification.objects.filter(recipient=request.user, unread=True, level='communication').order_by('id').first()
	celebracoes = Celebracao.objects.filter(data_celebracao=hoje, funcionario__in=[funcionario.id]).order_by('id')

	tipos = TipoAtividade.objects.all()
	atividades = Atividade.objects.filter(funcionarios=funcionario, data_finalizacao=None).values('titulo', 'inicio', 'final').order_by('inicio')
	humor = Humor.objects.filter(funcionario=funcionario, data_cadastro__date=hoje)
	perfil = Perfil.objects.get(funcionario=funcionario)
	ponto = Ponto.objects.filter(funcionario=funcionario).order_by('id').last()
	moedas = sum([i.pontuacao for i in Moeda.objects.filter(funcionario=funcionario, fechado=False)])

	pesquisas_pendentes = False
	for pesquisa in Pesquisa.objects.filter(funcionarios=funcionario, data_encerramento__gte=datetime.now().replace(tzinfo=pytz.utc)):
		if not Resposta.objects.filter(funcionario=funcionario, pergunta__pesquisa=pesquisa):
			pesquisas_pendentes = True

	pendencias = {
		'pesquisas': pesquisas_pendentes,
		'perfil': not_none_not_empty(funcionario.nome_mae, funcionario.nome_pai, funcionario.rg, funcionario.data_expedicao, funcionario.rua, funcionario.numero, funcionario.cep) is False,
		'cursos': ProgressoEtapa.objects.filter(funcionario=funcionario, data_conclusao=None).exists()
	}

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
				admin = Funcionario.objects.filter(data_demissao=None, matricula__in=[i.strip() for i in Variavel.objects.get(chave='RESP_USERS').valor.split(',')]).first()
				humor_choice = [i for i in Humor.Status.choices if i[0] == request.POST.get('mood')][0]
				Humor(humor=int(humor_choice[0]), funcionario=funcionario).save()
				add_coins(funcionario, 10)
				
				if int(humor_choice[0]) < 3:
					notify.send(
					sender=funcionario.usuario,
					recipient=admin.usuario,
					verb='Foi enviado um humor negativo',
					description=f'Atenção ao {funcionario.nome_completo}, está com o humor {humor_choice[1]}!'
				)
					
				messages.success(request, 'Obrigado por nos enviar seu humor!')

			except Exception as e:
				messages.error(request, f'Oops, ocorreu um erro ao enviar: {e}')

			return redirect('inicio')

	context = {
		'paginacao': paginacao,
		'posts': posts,
		'funcionarios': funcionarios,
		'funcionario': funcionario,
		'notificacoes': notificacoes,
		'comunicado': comunicado,
		'celebracoes': celebracoes,
		'tipos': tipos,
		'atividades': atividades,
		'humor': True if humor else False,
		'perfil': perfil,
		'ponto': datetime.combine(ponto.data, ponto.hora) if ponto else None,
		'pendencias': pendencias,
		'moedas': moedas
	}
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
			add_coins(funcionario, 5)
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
			funcionario = Funcionario.objects.get(usuario=request.user)
			postagem = Postagem.objects.get(pk=post, funcionario=funcionario)
			postagem.titulo = titulo
			postagem.texto = texto
			postagem.save()
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
		funcionario = Funcionario.objects.get(usuario=request.user)
		Postagem.objects.get(pk=post, funcionario=funcionario).delete()
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
			add_coins(funcionario, value)

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
@login_required(login_url='entrar')
def OuvidoriaView(request):
	funcionarios = Funcionario.objects.filter(data_demissao=None).order_by('nome_completo')
	funcionario = funcionarios.get(usuario=request.user)
	notificacoes = Notification.objects.filter(recipient=request.user, unread=True)

	tickets = Ouvidoria.objects.all()

	if not request.user.is_ouvidor:
		funcionarios = funcionarios.filter(pk=funcionario.pk)
		tickets = tickets.filter(funcionario=funcionario)

	context = {
		'funcionarios': funcionarios,
		'funcionario': funcionario,
		'notificacoes': notificacoes,
		'tickets': tickets,
		'categorias': [{'id': i[0], 'title': i[1]} for i in Ouvidoria.Categoria.choices]
	}
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
			ouvidoria = Ouvidoria.objects.create(
				funcionario=funcionario,
				responsavel=Funcionario.objects.filter(data_demissao=None, usuario__is_ouvidor=True).first(),
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

			add_coins(funcionario, 30)

			admin = Funcionario.objects.filter(data_demissao=None, matricula__in=[i.strip() for i in Variavel.objects.get(chave='RESP_USERS').valor.split(',')]).first()
			notify.send(
				sender=request.user,
				recipient=admin.usuario,
				verb=f'Uma manifestação foi aberta {ouvidoria.assunto} ({categoria[1]})',
			)

		messages.success(request, 'Manifestação enviada com sucesso!')

	except Exception as e:
		messages.error(request, f'Manifestação não foi salva! {e}')

	return redirect('ouvidoria')


# Modal
@login_required(login_url='entrar')
def AdicionarSugestaoView(request):
	try:
		Sugestao(
			tipo=request.POST.get('tipo'),
			modelo=request.POST.get('modelo'),
			mensagem=request.POST.get('mensagem'),
			funcionario=Funcionario.objects.get(usuario=request.user)
		).save()

		messages.success(request, 'Sugestão enviada com sucesso')

	except Exception as e:
		messages.error(request, f'Sugestão não foi enviada: {e}')

	return redirect('inicio')


# Page
@login_required(login_url='entrar')
def ScoreView(request):
	funcionarios = Funcionario.objects.filter(data_demissao=None).order_by('nome_completo')
	funcionario = funcionarios.get(usuario=request.user)
	notificacoes = Notification.objects.filter(recipient=request.user, unread=True)

	anomes = int(datetime.today().strftime('%Y%m'))
	pontuacoes_atuais = Moeda.objects.filter(anomes=anomes, fechado=False).order_by('-pontuacao')
	pontuacoes_fechadas = Moeda.objects.filter(fechado=True).exclude(anomes=anomes).order_by('-anomes', '-pontuacao')

	top = []
	if len(pontuacoes_atuais) >= 3:
		top.append(pontuacoes_atuais[:3])

	context = {
		'funcionarios': funcionarios,
		'funcionario': funcionario,
		'notificacoes': notificacoes,
		'pontuacoes_atuais': pontuacoes_atuais,
		'pontuacoes_fechadas': pontuacoes_fechadas,
		'top': top,
	}
	return render(request, 'pages/score.html', context)


# Modal
@login_required(login_url='entrar')
def AdicionarMoedaView(request, func, anomes):
	if not request.method == 'POST':
		messages.warning(request, 'Método não permitido!')
		return redirect('pontos')
	
	try:
		moeda = Moeda.objects.filter(funcionario__id=func, anomes=anomes, fechado=True).order_by('-id').first()
		moeda.pontuacao += int(request.POST.get('quantidade'))
		moeda.save()
		messages.success(request, 'Moedas inseridas com sucesso')

	except Exception as e:
		messages.error(request, f'Moedas não foram inseridas! {e}')

	return HttpResponseRedirect(request.META.get('HTTP_REFERER', '/'))
