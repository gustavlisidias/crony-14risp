from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.db.models import Q
from django.shortcuts import render, redirect
from django.utils import timezone

from datetime import datetime, timedelta

from configuracoes.models import Contrato
from cursos.models import Curso, Etapa, CursoFuncionario, ProgressoEtapa
from cursos.utils import progressao_cursos_funcionarios
from funcionarios.models import Funcionario
from ponto.renderers import gerar_certificado
from web.decorators import base_context_required
from web.utils import not_none_not_empty


# Page
@base_context_required
def CursoView(request, context):
	funcionarios = context['funcionarios']
	funcionario = context['funcionario']

	if request.user.get_access == 'common':
		funcionarios = funcionarios.filter(pk=funcionario.pk)

	if request.user.get_access == 'manager':
		funcionarios = funcionarios.filter(Q(gerente=funcionario) | Q(pk=funcionario.pk)).distinct()

	filtro_inicio = request.GET.get('data_inicial', (datetime.today() - timedelta(days=30)).strftime('%Y-%m-%d'))
	filtro_final = request.GET.get('data_final', timezone.localtime().strftime('%Y-%m-%d'))
	filtro_funcionarios = request.GET.getlist('funcionarios') if request.GET.get('funcionarios') else [i.id for i in funcionarios]
	filtros = {'inicio': filtro_inicio, 'final': filtro_final, 'funcionarios': filtro_funcionarios}

	cursos_disponiveis = Curso.objects.all().order_by('-data_cadastro')
	etapas = ProgressoEtapa.objects.filter(funcionario__id__in=filtro_funcionarios).order_by('etapa__id')
	etapas_criadas = Etapa.objects.all().order_by('id')
	contratos = Contrato.objects.all()

	cursos_por_funcionario = progressao_cursos_funcionarios(etapas, filtro_inicio, filtro_final)
	if not cursos_por_funcionario or max(len(v) for _, v in cursos_por_funcionario.items()) <= 0:
		cursos_por_funcionario = None
	
	cursos_ordenados = list()

	if cursos_por_funcionario:
		for func, cursos in cursos_por_funcionario.items():
			for curso, info in cursos.items():
				cursos_ordenados.append({
					'funcionario': func,
					'curso': curso,
					'info': info,
					'data_cadastro': curso.data_cadastro
				})
	
	cursos_ordenados = sorted(cursos_ordenados, key=lambda x: x['data_cadastro'], reverse=True)

	if request.method == 'POST':
		try:
			contratos_aplicados = Contrato.objects.filter(id__in=request.POST.getlist('contrato')) if not_none_not_empty(request.POST.getlist('contrato')) else list()

			if not_none_not_empty(request.POST.get('titulo')):
				with transaction.atomic():
					curso = Curso.objects.create(
						titulo=request.POST.get('titulo'),
						descricao=request.POST.get('descricao'),
						certificado=True if request.POST.get('certificado') == 'on' else False,
						observacao=request.POST.get('observacao'),
						tipo=request.POST.get('tipo_certificado')
					)

					if contratos_aplicados:
						curso.contrato.set([i.id for i in contratos_aplicados])
					
					if not_none_not_empty(request.POST.get('etapa')):
						for etapa in Etapa.objects.filter(pk__in=[int(i) for i in request.POST.getlist('etapa')]):
							etapa.curso.set([curso.id])

					if not_none_not_empty(request.POST.get('etapa_titulo')):
						for index, titulo in enumerate(request.POST.getlist('etapa_titulo')):
							nova_etapa = Etapa.objects.create(
								titulo=titulo,
								texto=request.POST.getlist('etapa_texto')[index]
							)

							nova_etapa.curso.set([curso.id])

					# Aplicar curso à Funcionarios
					for func in Funcionario.objects.filter(data_demissao=None):
						if func.get_contrato in contratos_aplicados:
							CursoFuncionario.objects.create(curso=curso, funcionario=func)

				messages.success(request, 'Curso adicionado com sucesso!')

			if not_none_not_empty(request.POST.get('curso')):
				curso = Curso.objects.get(pk=int(request.POST.get('curso')))
				CursoFuncionario(curso=curso, funcionario=funcionario).save()
				messages.success(request, 'Curso atribuido com sucesso!')

		except Exception as e:
			messages.error(request, f'Erro ao adicionar curso: {e}!')

		return redirect('cursos')

	context.update({
		'funcionarios': funcionarios,
		'filtros': filtros,
		'cursos_disponiveis': cursos_disponiveis,
		'cursos_por_funcionario': cursos_ordenados,
		'contratos': contratos,
		'etapas': etapas_criadas
	})

	return render(request, 'pages/cursos.html', context)


# Page
@base_context_required
def ProgressoCursoView(request, context, course, func):
	funcionario = context['funcionario']
	curso = Curso.objects.get(pk=course)
	colaborador = Funcionario.objects.get(pk=func)

	if funcionario != colaborador:
		messages.warning(request, 'Este curso está atribuído a outro funcionário!')
		return redirect('cursos')

	progresso = ProgressoEtapa.objects.filter(funcionario=colaborador, etapa__curso=curso).order_by('etapa__id')

	concluido = True if not ProgressoEtapa.objects.filter(funcionario=colaborador, etapa__curso=curso, data_conclusao=None) else False

	if request.POST.get('certificado'):
		if ProgressoEtapa.objects.filter(funcionario=colaborador, etapa__curso=curso, data_conclusao=None).exists():
			messages.warning(request, 'Você deve concluir todas as etapas antes de gerar seu certificado!')
			return redirect('progresso-curso', course, func)
		
		info = CursoFuncionario.objects.get(funcionario=colaborador, curso=curso)
		dados = {
			'funcionario': colaborador.nome_completo,
			'curso': curso.titulo,
			'tipo': curso.get_tipo_display(),
			'descricao': curso.observacao,
			'uuid': info.uuid,
			'data_conclusao': info.data_conclusao,
			'resp_nome': 'Anderson Luis Antonio',
			'resp_titulo': 'CEO & RH Manager',
			'dir_nome': 'Julio Cesar Coelho Neto',
			'dir_titulo': 'Operational Manager',
		}
		
		return gerar_certificado(dados)

	context.update({
		'curso': curso,
		'progresso': progresso,
		'concluido': concluido
	})

	return render(request, 'pages/cursos-progresso.html', context)


# Modal
@login_required(login_url='entrar')
def AtribuirCursoView(request, course):
	if not request.method == 'POST':
		messages.warning(request, 'Método não permitido!')
		return redirect('cursos')
	
	funcionarios = Funcionario.objects.filter(pk__in=request.POST.getlist('funcionarios'))
	curso = Curso.objects.get(pk=course)
	if not_none_not_empty(funcionarios, curso):
		for funcionario in funcionarios:
			CursoFuncionario(curso=curso, funcionario=funcionario).save()
				
		messages.success(request, 'Curso atribuído com sucesso!')
	
	else:
		messages.error(request, 'Insira todas as informações obrigatórias!')
	
	return redirect('cursos')


# Modal
@login_required(login_url='entrar')
def EditarCursoView(request, course):
	try:
		contratos_aplicados = Contrato.objects.filter(id__in=request.POST.getlist('contrato')) if not_none_not_empty(request.POST.getlist('contrato')) else list()

		if not_none_not_empty(request.POST.get('titulo')):
			with transaction.atomic():
				curso = Curso.objects.get(pk=course)

				curso.titulo = request.POST.get('titulo')
				curso.descricao = request.POST.get('descricao')
				curso.certificado = True if request.POST.get('certificado') == 'on' else False
				curso.observacao = request.POST.get('observacao')
				curso.tipo = request.POST.get('tipo_certificado')

				for i in Etapa.objects.filter(curso=curso):
					i.curso.clear()

				if contratos_aplicados:
					curso.contrato.set([i.id for i in contratos_aplicados])
				
				if not_none_not_empty(request.POST.get('etapa')):
					for etapa in Etapa.objects.filter(pk__in=[int(i) for i in request.POST.getlist('etapa')]):
						etapa.curso.set([curso.id])

				if not_none_not_empty(request.POST.get('etapa_titulo')):
					for index, titulo in enumerate(request.POST.getlist('etapa_titulo')):
						nova_etapa = Etapa.objects.create(
							titulo=titulo,
							texto=request.POST.getlist('etapa_texto')[index]
						)

						nova_etapa.curso.set([curso.id])

				curso.save()

				# Aplicar curso à Funcionarios
				for funcionario in Funcionario.objects.filter(data_demissao=None):
					if funcionario.get_contrato in contratos_aplicados:
						CursoFuncionario.objects.create(curso=curso, funcionario=funcionario)

				messages.success(request, 'Curso alterado com sucesso!')
	
	except Exception as e:
		messages.success(request, f'Curso não foi alterado! {e}')

	return redirect('cursos')
