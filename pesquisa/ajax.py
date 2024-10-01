from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse

from pesquisa.models import Pesquisa, Pergunta, Resposta


@login_required(login_url='entrar')
def VisualizarPesquisaView(request, pesqid):
	if not request.method == 'GET':
		messages.warning(request, 'Método não permitido!')
		return JsonResponse({'message': 'forbidden'}, status=404)

	try:
		pesquisa = Pesquisa.objects.get(pk=pesqid)
		pesquisa = {'id': pesquisa.id, 'titulo': pesquisa.titulo, 'descricao': pesquisa.descricao, 'anonimo': pesquisa.anonimo, 'encerramento': pesquisa.data_encerramento.strftime("%Y-%m-%d")}
		perguntas = list(Pergunta.objects.filter(pesquisa__id=pesqid).values('id', 'texto', 'obrigatorio'))
		respostas = list(Resposta.objects.filter(pergunta__pesquisa__id=pesqid).values('id', 'pergunta__texto', 'texto', 'funcionario__id', 'funcionario__nome_completo'))
		funcionarios = [i.id for i in Pesquisa.objects.get(pk=pesqid).funcionarios.all()]

		return JsonResponse({'pesquisa': pesquisa, 'perguntas': perguntas, 'respostas': respostas, 'funcionarios': funcionarios}, status=200)
	except Exception as e:
		return JsonResponse({'message': e}, status=400)


@login_required(login_url='entrar')
def ExcluirPesquisaView(request, pesqid):
	if not request.method == 'POST':
		messages.warning(request, 'Método não permitido!')
		return JsonResponse({'message': 'forbidden'}, status=404)

	if request.user.get_access != 'admin':
		messages.error(request, 'Você não tem permissão para excluir a notificação!')
		return JsonResponse({'message': 'not allowed'}, status=400)

	Pesquisa.objects.get(pk=pesqid).delete()
	messages.success(request, 'Pesquisa excluída com sucesso!')
	return JsonResponse({'message': 'success'}, status=200)
