from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.utils import timezone

from cursos.models import ProgressoEtapa, Curso, Etapa, CursoFuncionario
from funcionarios.models import Funcionario
from web.utils import add_coins


@login_required(login_url='entrar')
def ConcluirEtapaView(request, course, etapa):
	if request.method != 'POST':
		return JsonResponse({'message': 'Método não permitido!'}, status=404)

	try:
		curso = Curso.objects.get(pk=course)
		funcionario = Funcionario.objects.get(usuario=request.user)
		progresso = ProgressoEtapa.objects.get(pk=etapa, funcionario=funcionario)

		if not progresso.data_conclusao:
			progresso.data_conclusao = timezone.localtime()
			progresso.save()

			if not ProgressoEtapa.objects.filter(funcionario=funcionario, etapa__curso=curso, data_conclusao=None):
				CursoFuncionario.objects.filter(funcionario=funcionario, curso=curso).update(data_conclusao=timezone.localtime())
				add_coins(funcionario, 300, 'Conclusão de curso')
				return JsonResponse({'message': 'Curso concluído com sucesso. Faça download do seu certificado!', 'status': True}, status=200)

			return JsonResponse({'message': 'Etapa concluída com sucesso!'}, status=200)

		else:
			return JsonResponse({'message': 'Etapa já foi concluída anteriormente!'}, status=202)

	except Exception as e:
		return JsonResponse({'message': f'Etapa não foi concluída! {e}'}, status=400)


@login_required(login_url='entrar')
def ConsultarCursoView(request, course):
	if request.method != 'GET':
		return JsonResponse({'message': 'Método não permitido!'}, status=404)
	try:
		curso = Curso.objects.get(pk=course)

		etapas = [
			{
				'id': i.id,
				'titulo': i.titulo,
				'texto': i.texto
			} for i in Etapa.objects.filter(curso=curso).order_by('titulo')
		]

		response = {
			'curso': {
				'id': curso.id,
				'titulo': curso.titulo,
				'certificado': curso.certificado,
				'descricao': curso.descricao,
				'observacao': curso.observacao,
				'tipo': curso.tipo,
				'contratos': [j.id for j in curso.contrato.all()],
				'times': [j.id for j in curso.time.all()],
				'etapas': etapas
			},
		}

		return JsonResponse(response, status=200)

	except Exception as e:
		return JsonResponse({'message': f'Curso não foi alterado! {e}'}, status=400)
