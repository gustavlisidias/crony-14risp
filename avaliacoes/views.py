from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.db.models import Q
from django.http import HttpResponseRedirect
from django.shortcuts import render, redirect

from datetime import datetime
from slugify import slugify

from avaliacoes.models import Avaliacao, Nivel, Pergunta, PerguntaAvaliacao, Resposta
from avaliacoes.utils import dados_avaliacao
from funcionarios.models import Funcionario
from ponto.renderers import RenderToPDF
from web.decorators import base_context_required
from web.utils import not_none_not_empty


# Page
@base_context_required
def AvaliacaoView(request, context):
	funcionario = context['funcionario']

	if request.user.get_access == 'admin':
		avaliacoes = Avaliacao.objects.all()
	elif request.user.get_access == 'manager':
		avaliacoes = Avaliacao.objects.filter(Q(avaliadores__gerente=funcionario) | Q(avaliadores=funcionario)).distinct()
	else:
		avaliacoes = Avaliacao.objects.filter(avaliadores=funcionario)
	
	for avaliacao in avaliacoes:
		if funcionario in avaliacao.avaliadores.all():
			avaliacao.respondido = Resposta.objects.filter(funcionario=funcionario, referencia__avaliacao=avaliacao).exists()
		else:
			avaliacao.respondido = False

	niveis = [{'key': i[0], 'value': i[1]} for i in Nivel.Tipo.choices]
	perguntas = Pergunta.objects.all()

	if request.method == 'POST':
		try:
			avaliado = Funcionario.objects.get(pk=int(request.POST.get('avaliado')))

			with transaction.atomic():
				avaliacao = Avaliacao.objects.create(
					titulo=request.POST.get('titulo'),
					descricao=request.POST.get('descricao'),
					avaliado=avaliado,
					inicio=datetime.strptime(request.POST.get('inicio'), '%Y-%m-%d'),
					final=datetime.strptime(request.POST.get('final'), '%Y-%m-%d'),
					data_encerramento=datetime.strptime(request.POST.get('encerramento'), '%Y-%m-%d'),
				)

				avaliacao.avaliadores.set([int(i) for i in request.POST.getlist('avaliadores')])
				avaliacao.save()

				# Peso de cada nivel de avaliador na avaliação
				for obj in niveis:
					Nivel(
						avaliacao=avaliacao,
						tipo=obj['key'],
						peso=request.POST.get(obj['value'].lower())
					).save()

				# Se selecionei perguntas já prontas, guardo o id delas
				perguntas_avaliacao = list()
				if not_none_not_empty(request.POST.get('perguntas')):
					for i in request.POST.getlist('perguntas'):
						pergunta = Pergunta.objects.get(pk=int(i))
						perguntas_avaliacao.append(pergunta)

				# Se criei novas perguntas, salvo no banco e as adiciono na lista
				if not_none_not_empty(request.POST.get('nova-pergunta')):
					for i, _ in enumerate(request.POST.getlist('nova-pergunta')):
						if not not_none_not_empty(request.POST.get('pergunta-titulo[0]')):
							i += 1
						pergunta = Pergunta.objects.create(
							titulo=request.POST.get(f'pergunta-titulo[{i}]'),
							texto=request.POST.get(f'pergunta-texto[{i}]'),
							peso=request.POST.get(f'pergunta-peso[{i}]')
						)
						perguntas_avaliacao.append(pergunta)

				# Salvo as perguntas na tabela de relacionamento PerguntaAvaliacao
				for pergunta in perguntas_avaliacao:
					PerguntaAvaliacao(
						pergunta=pergunta,
						avaliacao=avaliacao
					).save()

				messages.success(request, 'Avaliação criada com sucesso!')

		except Exception as e:
			messages.error(request, f'Avaliação não foi criada! {e}')

		return HttpResponseRedirect(request.META.get('HTTP_REFERER', '/'))

	context.update({
		'avaliacoes': avaliacoes,
		'niveis': niveis,
		'perguntas': perguntas
	})

	return render(request, 'pages/avaliacao.html', context)


# Page
@base_context_required
def AvaliacaoDetalhesView(request, context, avaid):
	funcionario = context['funcionario']

	avaliacao = Avaliacao.objects.get(pk=avaid)
	perguntas = [i.pergunta for i in PerguntaAvaliacao.objects.filter(avaliacao=avaliacao)]
	respostas = Resposta.objects.filter(referencia__avaliacao=avaliacao)

	dados, grafico = dados_avaliacao(avaliacao, perguntas, respostas)

	if not_none_not_empty(request.GET.get('exportar')):
		filename = f'avaliacao_{slugify(avaliacao.avaliado.nome_completo.lower())}.pdf'
		context = {
			'autor': Funcionario.objects.get(usuario=request.user),
			'avaliacao': avaliacao,
			'perguntas': perguntas,
			'dados': dados,
			'grafico': grafico
		}
		return RenderToPDF(request, 'relatorios/avaliacao.html', context, filename).weasyprint()

	if request.method == 'POST':
		# Editar avaliação
		if request.POST.get('editar-avaliacao'):
			avaliacao.inicio = datetime.strptime(request.POST.get('inicio'), '%Y-%m-%d')
			avaliacao.final = datetime.strptime(request.POST.get('final'), '%Y-%m-%d')
			avaliacao.descricao = request.POST.get('descricao')
			avaliacao.data_encerramento = datetime.strptime(request.POST.get('encerramento'), '%Y-%m-%d')
			avaliacao.avaliadores.set([int(i) for i in request.POST.getlist('funcionarios')])
			avaliacao.save()
			messages.success(request, 'Avaliação alterada com sucesso!')
			return HttpResponseRedirect(request.META.get('HTTP_REFERER', '/'))
		
		# Encerrar avaliação
		elif request.POST.get('encerrar-avaliacao'):
			avaliacao.status = True
			avaliacao.save()
			messages.success(request, 'Avaliação encerrada com sucesso!')
			return HttpResponseRedirect(request.META.get('HTTP_REFERER', '/'))
		
		# Excluir avaliação
		elif request.POST.get('excluir-avaliacao'):
			avaliacao.delete()
			messages.success(request, 'Avaliação excluída com sucesso!')
			return redirect('avaliacao')
		
		# Responder avaliação
		else:
			try:
				for item in PerguntaAvaliacao.objects.filter(avaliacao=avaliacao):
					nota = float(request.POST.get(f'resposta-nota[{item.pergunta.id}]')) if request.POST.get(f'resposta-nota[{item.pergunta.id}]') else 0
					observacao = request.POST.get(f'resposta-observacao[{item.pergunta.id}]')
					Resposta(
						referencia=item,
						nota=nota,
						observacao=observacao,
						funcionario=funcionario
					).save()

				messages.success(request, 'Resposta enviada com sucesso!')

			except Exception as e:
				messages.error(request, f'Resposta não foi enviada! {e}')

			return HttpResponseRedirect(request.META.get('HTTP_REFERER', '/'))

	context.update({
		'avaliacao': avaliacao,
		'perguntas': perguntas,
		'respostas': respostas,
		'respondido': funcionario in [i.funcionario for i in respostas],
		'comentarios': True in [not_none_not_empty(i.observacao) for i in respostas],

		'dados': dados,
		'grafico': grafico
	})

	return render(request, 'pages/avaliacao-detalhes.html', context)


# Modal
@login_required(login_url='entrar')
def DuplicarAvaliacaoView(request, avaid):
	if request.user.get_access == 'common':
		messages.warning(request, 'Você não possui acesso para realizar essa ação!')
		return redirect('avaliacao')
	
	if request.method != 'POST':
		messages.warning(request, 'Método não permitido!')
		return redirect('avaliacao')

	try:
		avaliacao = Avaliacao.objects.get(pk=avaid)
		
		with transaction.atomic():
			nova_avaliacao = Avaliacao.objects.create(
				titulo=avaliacao.titulo,
				descricao=avaliacao.descricao,
				avaliado=Funcionario.objects.get(pk=int(request.POST.get('novo_avaliado'))),
				inicio=avaliacao.inicio,
				final=avaliacao.final,
				data_encerramento=avaliacao.data_encerramento,
			)

			nova_avaliacao.avaliadores.set([i.id for i in avaliacao.avaliadores.all()])
			nova_avaliacao.save()

			for nivel in Nivel.objects.filter(avaliacao=avaliacao):
				Nivel.objects.create(
					avaliacao=nova_avaliacao,
					tipo=nivel.tipo,
					peso=nivel.peso
				)

			for item in PerguntaAvaliacao.objects.filter(avaliacao=avaliacao):
				PerguntaAvaliacao.objects.create(
					pergunta=item.pergunta,
					avaliacao=nova_avaliacao
				)

		messages.success(request, 'Avaliação duplicada com sucesso!')

	except Exception as e:
		messages.error(request, f'Avaliação não foi duplicada! {e}')

	return redirect('avaliacao')
