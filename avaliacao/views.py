from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.db.models import Q
from django.http import HttpResponseRedirect
from django.shortcuts import render, redirect

from datetime import datetime
from slugify import slugify

from avaliacao.models import Avaliacao, PesoAvaliador, Criterio, Pergunta, PesoCriterio, Resposta
from avaliacao.utils import dados_avaliacao
from funcionarios.models import Funcionario
from notifications.models import Notification
from ponto.renderers import RenderToPDF
from web.utils import not_none_not_empty


# Page
@login_required(login_url='entrar')
def AvaliacaoView(request):
	funcionarios = Funcionario.objects.filter(data_demissao=None).order_by('nome_completo')
	funcionario = funcionarios.get(usuario=request.user)
	notificacoes = Notification.objects.filter(recipient=request.user, unread=True)

	if request.user.get_access == 'admin':
		avaliacoes = Avaliacao.objects.all()
	elif request.user.get_access == 'manager':
		avaliacoes = Avaliacao.objects.filter(Q(avaliadores__gerente=funcionario) | Q(avaliadores=funcionario)).distinct()
	else:
		avaliacoes = Avaliacao.objects.filter(avaliadores=funcionario)

	niveis = [{'key': i[0], 'value': i[1]} for i in PesoAvaliador.Nivel.choices]
	criterios = Criterio.objects.all()
	perguntas = Pergunta.objects.all()

	if request.method == 'POST':
		try:
			avaliado = Funcionario.objects.get(pk=int(request.POST.get('avaliado')))
			perguntas_avaliacao = list()

			with transaction.atomic():
				avaliacao = Avaliacao.objects.create(
					titulo=request.POST.get('titulo'),
					descricao=request.POST.get('descricao'),
					avaliado=avaliado,
					inicio=datetime.strptime(request.POST.get('inicio'), '%Y-%m-%d'),
					final=datetime.strptime(request.POST.get('final'), '%Y-%m-%d'),
					data_encerramento=datetime.strptime(request.POST.get('encerramento'), '%Y-%m-%d'),
				)

				avaliacao.avaliadores.set([int(i) for i in request.POST.getlist('funcionarios')])
				avaliacao.save()

				# Peso de cada nivel de avaliador na avaliação
				for nivel in niveis:
					PesoAvaliador(
						avaliacao=avaliacao,
						nivel=nivel['key'],
						peso=request.POST.get(nivel['value'].lower())
					).save()

				# Se selecionei perguntas já prontas, guardo o id delas
				if not_none_not_empty(request.POST.get('perguntas')):
					for i in request.POST.getlist('perguntas'):
						pergunta = Pergunta.objects.get(pk=int(i))
						perguntas_avaliacao.append(pergunta.id)

				# Se criei novas perguntas, salvo no banco e as adiciono na lista
				if not_none_not_empty(request.POST.get('texto-pergunta-nova')):
					novos_titulos = request.POST.getlist('titulo-pergunta-nova')
					novas_perguntas = request.POST.getlist('texto-pergunta-nova')
					for i, texto in enumerate(novas_perguntas):
						pergunta = Pergunta.objects.create(
							titulo=novos_titulos[i],
							texto=texto
						)
						perguntas_avaliacao.append(pergunta.id)

				# Peso de cada criterio de cada pergunta na avaliação
				for pergunta in Pergunta.objects.filter(pk__in=perguntas_avaliacao):
					for criterio in criterios:
						PesoCriterio(
							avaliacao=avaliacao,
							pergunta=pergunta,
							criterio=criterio,
							peso=request.POST.get(criterio.nome.lower())
						).save()

				messages.success(request, 'Avaliação criada com sucesso!')

		except Exception as e:
			messages.error(request, f'Avaliação não foi criada! {e}')

		return HttpResponseRedirect(request.META.get('HTTP_REFERER', '/'))

	context = {
		'funcionarios': funcionarios,
		'funcionario': funcionario,
		'notificacoes': notificacoes,

		'avaliacoes': avaliacoes,
		'niveis': niveis,
		'criterios': criterios,
		'perguntas': perguntas
	}
	return render(request, 'pages/avaliacao.html', context)


# Page
@login_required(login_url='entrar')
def AvaliacaoDetalhesView(request, avaid):
	funcionarios = Funcionario.objects.filter(data_demissao=None).order_by('nome_completo')
	funcionario = funcionarios.get(usuario=request.user)
	notificacoes = Notification.objects.filter(recipient=request.user, unread=True)

	avaliacao = Avaliacao.objects.get(pk=avaid)
	perguntas = PesoCriterio.objects.filter(avaliacao=avaliacao)
	if request.user.get_access != 'common':
		respostas = Resposta.objects.filter(pergunta__avaliacao=avaliacao)
	else:
		respostas = Resposta.objects.filter(pergunta__avaliacao=avaliacao, funcionario=funcionario)
	respondido = funcionario in [i.funcionario for i in respostas]

	if respostas:
		dados = dados_avaliacao(avaliacao, respostas)
	else:
		dados = None

	if request.method == 'GET' and not_none_not_empty(request.GET.get('exportar')):
		filename = f'avaliacao_{slugify(avaliacao.avaliado.nome_completo.lower())}.pdf'
		context = {
			'autor': Funcionario.objects.get(usuario=request.user),
			'avaliacao': avaliacao,
			'perguntas': perguntas,
			'dados': dados
		}
		return RenderToPDF(request, 'relatorios/avaliacao.html', context, filename).weasyprint()

	if request.method == 'POST':
		if request.POST.get('salvar'):
			avaliacao.inicio = datetime.strptime(request.POST.get('inicio'), '%Y-%m-%d')
			avaliacao.final = datetime.strptime(request.POST.get('final'), '%Y-%m-%d')
			avaliacao.data_encerramento = datetime.strptime(request.POST.get('encerramento'), '%Y-%m-%d')
			avaliacao.avaliadores.set([int(i) for i in request.POST.getlist('funcionarios')])
			avaliacao.save()
			messages.success(request, 'Avaliação alterada com sucesso!')
			return HttpResponseRedirect(request.META.get('HTTP_REFERER', '/'))
		
		if request.POST.get('encerrar'):
			avaliacao.status = True
			avaliacao.save()
			messages.success(request, 'Avaliação encerrada com sucesso!')
			return HttpResponseRedirect(request.META.get('HTTP_REFERER', '/'))
		
		if request.POST.get('excluir'):
			avaliacao.delete()
			messages.success(request, 'Avaliação excluída com sucesso!')
			return redirect('avaliacao')
		
		else:
			try:
				for obj in perguntas:
					Resposta(
						pergunta=obj,
						nota=request.POST.get(f'{obj.pergunta.titulo.lower()}-{obj.criterio.nome.lower()}'),
						observacao=request.POST.get(f'{obj.pergunta.titulo.lower()}-observacao'),
						funcionario=funcionario
					).save()

				messages.success(request, 'Resposta enviada com sucesso!')

			except Exception as e:
				messages.error(request, f'Resposta não foi enviada! {e}')

			return HttpResponseRedirect(request.META.get('HTTP_REFERER', '/'))

	context = {
		'funcionarios': funcionarios,
		'funcionario': funcionario,
		'notificacoes': notificacoes,

		'avaliacao': avaliacao,
		'perguntas': perguntas,
		'respostas': respostas,
		'respondido': respondido,
		'comentarios': True in [not_none_not_empty(i.observacao) for i in respostas],
		'dados': dados
	}
	return render(request, 'pages/avaliacao-detalhes.html', context)
