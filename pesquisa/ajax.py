from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse

from pesquisa.models import Pesquisa, Pergunta, Resposta, TextoPerguntas


@login_required(login_url='entrar')
def VisualizarPesquisaView(request, pesqid):
	if not request.method == 'GET':
		messages.warning(request, 'Método não permitido!')
		return JsonResponse({'message': 'forbidden'}, status=404)

	try:
		pesquisa = Pesquisa.objects.get(pk=pesqid)

		response = {
			'pesquisa': {
				'id': pesquisa.id,
				'titulo': pesquisa.titulo,
				'descricao': pesquisa.descricao,
				'anonimo': pesquisa.anonimo,
				'encerramento': pesquisa.data_encerramento.strftime("%Y-%m-%d")
			},
			'perguntas': [{
				'id': i.id,
				'titulo': i.titulo,
				'tipo': i.tipo,
				'obrigatorio': i.obrigatorio,
				'opcoes': [j.texto for j in TextoPerguntas.objects.filter(pergunta__id=i.id)]
			} for i in Pergunta.objects.filter(pesquisa=pesquisa)],
			'respostas': [{
				'id': i.id,
				'texto': i.texto,
				'funcionario': {'id': i.funcionario.id, 'nome_completo': i.funcionario.nome_completo},
			} for i in Resposta.objects.filter(pergunta__pesquisa=pesquisa)],
			'funcionarios': [{'id': i.id, 'nome_completo': i.nome_completo} for i in pesquisa.funcionarios.all()]
		}

		return JsonResponse(response, status=200)
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
