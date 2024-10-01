from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.utils import timezone

from cursos.models import ProgressoEtapa
from funcionarios.models import Funcionario
from web.utils import add_coins


@login_required(login_url='entrar')
def ConcluirEtapaView(request, etapa):
	if request.method != 'POST':
		return JsonResponse({'message': 'Método não permitido!'}, status=404)

	try:
		funcionario = Funcionario.objects.get(usuario=request.user)
		progresso = ProgressoEtapa.objects.get(pk=etapa, funcionario=funcionario)
		if not progresso.data_conclusao:
			progresso.data_conclusao = timezone.localtime()
			progresso.save()

			if not ProgressoEtapa.objects.filter(funcionario=funcionario, data_conclusao=None):
				add_coins(funcionario, 300)

			return JsonResponse({'message': 'Etapa concluída com sucesso!'}, status=200)

		else:
			return JsonResponse({'message': 'Etapa já foi concluída anteriormente!'}, status=202)

	except Exception as e:
		return JsonResponse({'message': f'Etapa não foi concluída! {e}'}, status=400)
