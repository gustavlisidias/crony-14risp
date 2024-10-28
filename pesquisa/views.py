import pytz

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.shortcuts import render, redirect

from datetime import datetime

from funcionarios.models import Funcionario
from notifications.models import Notification
from pesquisa.models import Pesquisa, Pergunta, Resposta
from web.report import gerar_relatorio_csv
from web.utils import not_none_not_empty, add_coins


# Page
@login_required(login_url='entrar')
def PesquisaView(request):
	funcionarios = Funcionario.objects.filter(data_demissao=None).order_by('nome_completo')
	funcionario = funcionarios.get(usuario=request.user)
	notificacoes = Notification.objects.filter(recipient=request.user, unread=True)

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
			titulo = request.POST.get('titulo')
			descricao = request.POST.get('descricao')
			data_encerramento = request.POST.get('data_encerramento')
			anonimo = True if request.POST.get('anonimo') else False
			perguntas = request.POST.getlist('pergunta')

			with transaction.atomic():
				pesquisa = Pesquisa.objects.create(
					titulo=titulo,
					descricao=descricao,
					data_encerramento=data_encerramento,
					anonimo=anonimo
				)

				for i, pergunta in enumerate(perguntas):
					obrigatorio = not_none_not_empty(request.POST.get(f'obrigatorio[{i+1}]'))
					Pergunta.objects.create(
						pesquisa=pesquisa,
						texto=pergunta,
						obrigatorio=obrigatorio
					)
			messages.success(request, 'Pesquisa criada com sucesso!')

		except Exception as e:
			messages.error(request, f'Pesquisa não foi criada com sucesso! {e}')

		return redirect('pesquisa')

	context = {
		'funcionarios': funcionarios,
		'funcionario': funcionario,
		'notificacoes': notificacoes,

		'pesquisas': pesquisas,
	}
	return render(request, 'pages/pesquisas.html', context)


# Page
@login_required(login_url='entrar')
def VisualizarRespostasView(request, pesqid):
	funcionarios = Funcionario.objects.filter(data_demissao=None).order_by('nome_completo')
	funcionario = funcionarios.get(usuario=request.user)
	notificacoes = Notification.objects.filter(recipient=request.user, unread=True)

	hoje = datetime.now().replace(tzinfo=pytz.utc)
	pesquisa = Pesquisa.objects.get(pk=pesqid)
	pesquisa.perguntas = Pergunta.objects.filter(pesquisa=pesquisa)
	pesquisa.respostas = Resposta.objects.filter(pergunta__pesquisa=pesquisa)

	dados = []
	for pergunta in pesquisa.perguntas:
		resposta_textos = [resposta.texto for resposta in pesquisa.respostas if resposta.pergunta.id == pergunta.id]
		count = [resposta_textos.count(texto) for texto in set(resposta_textos)]
		dados.append({
			'pergunta': pergunta.texto,
			'respostas': list(set(resposta_textos)),
			'count': count
		})

	if request.GET.get('exportar'):
		filename = f'relatorio_pesquisa_{pesquisa.titulo.lower()}'
		colunas = ['Funcionário', 'Pergunta', 'Resposta']

		dataset = list(pesquisa.respostas.values_list(
			'funcionario__nome_completo', 'pergunta__texto', 'texto'
		))		

		return gerar_relatorio_csv(colunas, dataset, filename)

	context = {
		'funcionarios': funcionarios,
		'funcionario': funcionario,
		'notificacoes': notificacoes,

		'pesquisa': pesquisa,
		'vencido': pesquisa.data_encerramento < hoje,
		'dados': dados
	}
	return render(request, 'pages/respostas-pesquisa.html', context)


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
		for index, pergid in enumerate(request.POST.getlist('pergunta')):
			Resposta(
				pergunta=Pergunta.objects.get(pk=pergid),
				texto=request.POST.getlist('resposta')[index],
				funcionario=funcionario
			).save()

		add_coins(funcionario, 150)
		messages.success(request, 'Respostas enviadas com sucesso!')

	except Exception as e:
		messages.error(request, f'Respostas não foram enviadas! {e}')

	return redirect('pesquisa')
