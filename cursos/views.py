from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.db.models import Q
from django.shortcuts import render, redirect
from django.utils import timezone

from datetime import timedelta

from configuracoes.models import Contrato
from cursos.models import Curso, Etapa, CursoFuncionario, ProgressoEtapa
from cursos.utils import progressao_cursos_funcionarios
from funcionarios.models import Funcionario
from notifications.models import Notification
from web.utils import not_none_not_empty


# Page
@login_required(login_url='entrar')
def CursoView(request):
	funcionarios = Funcionario.objects.filter(data_demissao=None).order_by('nome_completo')
	funcionario = funcionarios.get(usuario=request.user)
	notificacoes = Notification.objects.filter(recipient=request.user, unread=True)

	if request.user.get_access == 'common':
		funcionarios = funcionarios.filter(pk=funcionario.pk)

	if request.user.get_access == 'manager':
		funcionarios = funcionarios.filter(Q(gerente=funcionario) | Q(pk=funcionario.pk)).distinct()

	filtro_inicio = request.GET.get('data_inicial') if request.GET.get('data_inicial') else (timezone.localtime() - timedelta(days=29)).strftime('%Y-%m-%d')
	filtro_final = request.GET.get('data_final') if request.GET.get('data_final') else timezone.localtime().strftime('%Y-%m-%d')
	filtro_funcionarios = request.GET.getlist('funcionarios') if request.GET.get('funcionarios') else [i.id for i in funcionarios]
	filtros = {'inicio': filtro_inicio, 'final': filtro_final, 'funcionarios': filtro_funcionarios}

	cursos = Curso.objects.all()
	etapas = ProgressoEtapa.objects.filter(funcionario__id__in=filtro_funcionarios)
	etapas_criadas = Etapa.objects.all().order_by('titulo')
	cursos_por_funcionario = progressao_cursos_funcionarios(etapas, filtro_inicio, filtro_final)

	contratos = Contrato.objects.all()

	if request.method == 'POST':
		try:
			if not_none_not_empty(request.POST.get('titulo')):
				with transaction.atomic():
					curso = Curso.objects.create(
						titulo=request.POST.get('titulo'),
						descricao=request.POST.get('descricao'),
					)

					if not_none_not_empty(request.POST.get('contrato')):
						curso.contrato.set(request.POST.getlist('contrato'))
					
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

				messages.success(request, 'Curso adicionado com sucesso!')

			if not_none_not_empty(request.POST.get('curso')):
				curso = Curso.objects.get(pk=int(request.POST.get('curso')))
				CursoFuncionario(curso=curso, funcionario=funcionario).save()
				messages.success(request, 'Curso atribuido com sucesso!')

		except Exception as e:
			messages.error(request, f'Erro ao adicionar curso: {e}!')

		return redirect('cursos')

	context = {
		'funcionarios': funcionarios,
		'funcionario': funcionario,
		'notificacoes': notificacoes,
		'filtros': filtros,
		'cursos': cursos,
		'cursos_por_funcionario': cursos_por_funcionario,
		'contratos': contratos,
		'etapas': etapas_criadas
	}
	return render(request, 'pages/cursos.html', context)


# Page
@login_required(login_url='entrar')
def ProgressoCursoView(request, course, func):
	funcionarios = Funcionario.objects.filter(data_demissao=None).order_by('nome_completo')
	funcionario = funcionarios.get(usuario=request.user)
	notificacoes = Notification.objects.filter(recipient=request.user, unread=True)

	curso = Curso.objects.get(pk=course)
	funcionario_curso = funcionarios.get(pk=func)

	if funcionario != funcionario_curso:
		messages.warning(request, 'Este curso está atribuído a outro funcionário!')
		return redirect('cursos')

	progresso = ProgressoEtapa.objects.filter(funcionario=funcionario_curso, etapa__curso=curso)

	context = {
		'funcionarios': funcionarios,
		'funcionario': funcionario,
		'notificacoes': notificacoes,
		'curso': curso,
		'progresso': progresso,
	}
	return render(request, 'pages/progresso-curso.html', context)


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
