from django.contrib import messages
from django.contrib.contenttypes.models import ContentType
from django.http import JsonResponse
from django.shortcuts import redirect, get_object_or_404

from cities_light.models import SubRegion as Cidade
from funcionarios.models import Funcionario, Perfil
from web.models import Curtida, Postagem, Ouvidoria, MensagemOuvidoria, Celebracao, Comentario
from web.utils import not_none_not_empty, add_coins


def CurtirPostView(request, post, modelo):
	if request.method != 'POST':
		return JsonResponse({'mensagem': 'Método não permitido.'}, status=400)

	if modelo == 'postagem':
		model = Postagem
		value = 5
	elif modelo == 'celebracao':
		model = Celebracao
		value = 10
	else:
		return JsonResponse({'mensagem': 'Tipo de objeto inválido.'}, status=400)

	obj = get_object_or_404(model, pk=post)
	content_type = ContentType.objects.get_for_model(model)
	funcionario = get_object_or_404(Funcionario, usuario=request.user)

	try:
		curtida = Curtida.objects.get(content_type=content_type, object_id=obj.id, funcionario=funcionario)
		curtida.delete()
		add_coins(funcionario, -1 * value)
		return JsonResponse({'mensagem': 'disliked'}, status=200)
	
	except Curtida.DoesNotExist:
		Curtida.objects.create(content_type=content_type, object_id=obj.id, funcionario=funcionario)
		add_coins(funcionario, value)
		return JsonResponse({'mensagem': 'liked'}, status=200)
	

def VisualizarReacoesView(request, post, modelo):
	if not request.method == 'GET':
		return JsonResponse({'mensagem': 'Método não permitido.'}, status=400)
	
	if modelo == 'postagem':
		model = Postagem
	elif modelo == 'celebracao':
		model = Celebracao
	else:
		return JsonResponse({'mensagem': 'Tipo de objeto inválido.'}, status=400)
	
	obj = get_object_or_404(model, pk=post)

	try:
		reacoes = {'curtidas': list(obj.curtidas.values('funcionario__nome_completo', 'data_cadastro')), 'post': obj.titulo}
		return JsonResponse(reacoes, safe=False, status=200)

	except Exception as e:
		return JsonResponse({'mensagem': f'Ocorreu um erro: {str(e)}'}, status=500)
	

def VisualizarComentariosView(request, post, modelo):	
	if modelo == 'postagem':
		model = Postagem
	elif modelo == 'celebracao':
		model = Celebracao
	else:
		return JsonResponse({'mensagem': 'Tipo de objeto inválido.'}, status=400)
	
	obj = get_object_or_404(model, pk=post)
	content_type = ContentType.objects.get_for_model(model)
	funcionario = get_object_or_404(Funcionario, usuario=request.user)
	
	if request.method == 'POST':
		try:
			if not_none_not_empty(request.POST.get('remover')):
				Comentario.objects.get(pk=request.POST.get('remover')).delete()
				messages.success(request, 'Comentário removido com sucesso!')
			else:
				Comentario.objects.create(content_type=content_type, object_id=obj.id, funcionario=funcionario, comentario=request.POST.get('comentario'))
				messages.success(request, 'Comentário enviado com sucesso!')

			return redirect('inicio')
		
		except Exception as e:
			return JsonResponse({'mensagem': f'Ocorreu um erro: {str(e)}'}, status=500)
	
	if request.method == 'GET':
		try:
			comentarios = {'comentarios': list(obj.comentarios.values('id', 'funcionario__nome_completo', 'funcionario__usuario__id', 'data_cadastro', 'comentario')), 'post': obj.titulo}
			return JsonResponse(comentarios, safe=False, status=200)

		except Exception as e:
			return JsonResponse({'mensagem': f'Ocorreu um erro: {str(e)}'}, status=500)


def ProcurarCidadesView(request, estado):
	if not request.method == 'GET':
		return JsonResponse({'mensagem': 'Método não permitido.'}, status=400)

	try:
		cidades = list(Cidade.objects.filter(region_id=estado).values('id', 'name').order_by('name'))

		if cidades:
			return JsonResponse(cidades, safe=False, status=200)
		else:
			return JsonResponse({'mensagem': 'Não foram encontradas cidades para este estado'}, status=404)

	except Exception as e:
		return JsonResponse({'mensagem': f'Ocorreu um erro: {str(e)}'}, status=500)
	

def FuncionariosTagsView(request):
	if not request.method == 'GET':
		return JsonResponse({'mensagem': 'Método não permitido.'}, status=400)

	try:
		funcionarios = Funcionario.objects.filter(data_demissao=None)
		tags = {
            'feeds': [{
				'marker': '@',
				'feed': [i.get_tag for i in funcionarios],
				'minimumCharacters': 1
            }]
		}

		return JsonResponse(tags, status=200)

	except Exception as e:
		return JsonResponse({'mensagem': f'Ocorreu um erro: {str(e)}'}, status=500)


def EditarOuvidoriaView(request, ticket):
	ouvidoria = Ouvidoria.objects.get(pk=ticket)
	mensagens = MensagemOuvidoria.objects.filter(ticket=ouvidoria)

	if request.method == 'POST':
		if request.user != ouvidoria.funcionario.usuario or request.user != ouvidoria.responsavel.usuario:
			messages.warning(request, 'Você não possui permissão para realizar essa ação!')
			return redirect('ouvidoria')
			
		try:
			if not_none_not_empty(request.POST.get('finalizar')):
				ouvidoria.status = 2
				ouvidoria.save()
				
			else:
				MensagemOuvidoria(
					ticket=ouvidoria,
					mensagem=request.POST.get('mensagem'),
					remetente=Funcionario.objects.get(usuario=request.user)
				).save()

				ouvidoria.status = 3
				ouvidoria.save()

			messages.success(request, 'Mensagem enviada com sucesso!')
			return redirect('ouvidoria')

		except Exception as e:
			return JsonResponse({'mensagem': f'Ocorreu um erro: {str(e)}'}, status=500)
	
	if request.method == 'GET':
		try:
			data = list(mensagens.values_list('remetente__nome_completo', 'remetente__usuario', 'mensagem', 'data_cadastro__date').order_by('id'))
			context = {'data': data, 'anonimo': ouvidoria.anonimo}
			return JsonResponse(context, safe=False, status=200)

		except Exception as e:
			return JsonResponse({'mensagem': f'Ocorreu um erro: {str(e)}'}, status=500)


def AlterarTemaView(request):
	if not request.method == 'POST':
		return JsonResponse({'mensagem': 'Método não permitido.'}, status=400)

	try:
		funcionario = Funcionario.objects.get(usuario=request.user)
		perfil = Perfil.objects.get(funcionario=funcionario)

		if perfil.tema == 'light':
			perfil.tema = 'dark'
		else:
			perfil.tema = 'light'

		perfil.save()

		return JsonResponse({'mensagem': 'sucesso'}, safe=False, status=200)

	except Exception as e:
		return JsonResponse({'mensagem': f'Ocorreu um erro: {str(e)}'}, status=500)
