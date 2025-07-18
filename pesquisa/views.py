import pytz

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.shortcuts import render, redirect
from django.utils.text import slugify

from datetime import datetime

from funcionarios.models import Funcionario
from pesquisa.models import Pesquisa, Pergunta, Resposta, TextoPerguntas
from web.decorators import base_context_required
from web.report import gerar_relatorio_csv
from web.utils import not_none_not_empty, add_coins


# Page
@base_context_required
def PesquisaView(request, context):
	funcionario = context['funcionario']
	tipos = [{'key': i[0], 'value': i[1]} for i in Pergunta.Tipo.choices]

	if request.user.get_access == "admin":
		pesquisas = Pesquisa.objects.all().order_by('-data_cadastro')
	else:
		pesquisas = Pesquisa.objects.filter(funcionarios=funcionario).order_by('-data_cadastro')

	for pesquisa in pesquisas:
		pesquisa.perguntas = Pergunta.objects.filter(pesquisa=pesquisa)
		pesquisa.respostas = Resposta.objects.filter(pergunta__pesquisa=pesquisa)
		pesquisa.respondido = True if Resposta.objects.filter(funcionario=funcionario, pergunta__pesquisa=pesquisa).exists() else False

	if request.method == 'POST':
		try:
			with transaction.atomic():
				pesquisa = Pesquisa.objects.create(
					titulo=request.POST.get('titulo'),
					descricao=request.POST.get('descricao'),
					anonimo=True if request.POST.get('anonimo') else False,
					data_encerramento=request.POST.get('data_encerramento')
				)

				perguntas = request.POST.getlist('perguntas')
				for i, pergunta in enumerate(perguntas):
					obrigatorio = True if request.POST.get(f'pergunta_obrigatorio[{i+1}]') else False
					pergunta = Pergunta.objects.create(
						pesquisa=pesquisa,
						titulo=request.POST.get(f'pergunta_titulo[{i+1}]'),
						tipo=request.POST.get(f'pergunta_tipo[{i+1}]'),
						obrigatorio=obrigatorio
					)

					opcoes = request.POST.getlist(f'opcoes[{i+1}]')
					for j, _ in enumerate(opcoes):
						print(i+1, j+1)
						TextoPerguntas.objects.create(
							pergunta=pergunta,
							texto=request.POST.get(f'pergunta_opcao[{i+1}][{j+1}]')
						)

			messages.success(request, 'Pesquisa criada com sucesso!')

		except Exception as e:
			messages.error(request, f'Pesquisa não foi criada com sucesso! {e}')

		return redirect('pesquisa')

	context.update({
		'tipos': tipos,
		'pesquisas': pesquisas,
	})

	return render(request, 'pages/pesquisas.html', context)


# Page
@base_context_required
def VisualizarRespostasView(request, context, pesqid):
	hoje = datetime.now().replace(tzinfo=pytz.utc)
	funcionario = context['funcionario']	
	pesquisa = Pesquisa.objects.get(pk=pesqid)
	pesquisa.perguntas = Pergunta.objects.filter(pesquisa=pesquisa)
	pesquisa.respostas = Resposta.objects.filter(pergunta__pesquisa=pesquisa)

	dados = list()
	for pergunta in pesquisa.perguntas:
		resposta_textos = [resposta.texto for resposta in pesquisa.respostas if resposta.pergunta.id == pergunta.id]
		count = [resposta_textos.count(texto) for texto in set(resposta_textos)]
		dados.append({
			'pergunta': pergunta.titulo,
			'respostas': list(set(resposta_textos)),
			'count': count
		})

	if request.GET.get('exportar'):
		filename = f'relatorio_pesquisa_{slugify(pesquisa.titulo.lower())}'
		colunas = ['Funcionário', 'Pergunta', 'Resposta']

		dataset = list(pesquisa.respostas.values_list(
			'funcionario__nome_completo', 'pergunta__titulo', 'texto'
		))
		
		usuarios_respostas = set([i[0] for i in dataset])
		for funcionario in pesquisa.funcionarios.all():
			if funcionario.nome_completo not in usuarios_respostas:
				dataset.append((funcionario.nome_completo, '-', '-'))

		return gerar_relatorio_csv(colunas, dataset, filename)

	context.update({
		'pesquisa': pesquisa,
		'vencido': pesquisa.data_encerramento < hoje.date(),
		'dados': dados
	})

	return render(request, 'pages/pesquisas-resposta.html', context)


# Modal
@login_required(login_url='entrar')
def EditarPesquisaView(request, pesqid):
	if not request.method == 'POST':
		messages.warning(request, 'Método não permitido!')
		return redirect('pesquisa')
	
	try:
		pesquisa = Pesquisa.objects.get(pk=pesqid)
		pesquisa.descricao = request.POST.get('descricao')
		pesquisa.anonimo = True if not_none_not_empty(request.POST.get('anonimo')) else False
		pesquisa.data_encerramento = request.POST.get('data_encerramento')
		pesquisa.funcionarios.set(request.POST.getlist('funcionarios'))
		pesquisa.save()
		messages.success(request, 'Pesquisa alterada com sucesso!')

	except Exception as e:
		messages.error(request, f'Pesquisa não foi alterada! {e}')
	
	return redirect('pesquisa')


# Modal
@login_required(login_url='entrar')
def ResponderPesquisaView(request, pesqid):
	try:
		funcionario = Funcionario.objects.get(usuario=request.user)
		pesquisa = Pesquisa.objects.get(pk=pesqid)
		
		for pergunta in Pergunta.objects.filter(pesquisa=pesquisa):
			for resposta in request.POST.getlist(f'resposta_{pergunta.id}'):
				Resposta(
					pergunta=pergunta,
					texto=resposta,
					funcionario=funcionario
				).save()
		
		add_coins(funcionario, 150, 'Resposta de pesquisa')
		messages.success(request, 'Respostas enviadas com sucesso!')

	except Exception as e:
		messages.error(request, f'Respostas não foram enviadas! {e}')

	return redirect('pesquisa')
