from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse

from notifications.models import Notification


@login_required(login_url='entrar')
def LerNotificacaoView(request, notid):
	if not request.method == 'POST':
		return JsonResponse({'mensagem': 'Método não permitido.'}, status=400)

	try:
		notificacao = Notification.objects.get(pk=notid)
		notificacao.unread = False
		notificacao.save()
		return JsonResponse({'mensagem': 'deleted'}, status=200)

	except Exception as e:
		return JsonResponse({'mensagem': e}, status=404)


@login_required(login_url='entrar')
def LerTodasNotificacoesView(request):
	if not request.method == 'POST':
		return JsonResponse({'mensagem': 'Método não permitido.'}, status=400)

	try:
		notificacoes = Notification.objects.filter(recipient=request.user, unread=True)
		for notificacao in notificacoes:
			notificacao.unread = False
			notificacao.save()

		return JsonResponse({'mensagem': 'deleted'}, status=200)

	except Exception as e:
		return JsonResponse({'mensagem': e}, status=404)


@login_required(login_url='entrar')
def ExcluirNotificacaoView(request, notid):
	if not request.method == 'POST':
		messages.warning(request, 'Método não permitido!')
		return JsonResponse({'message': 'forbidden'}, status=404)

	if request.user.get_access == 'common':
		messages.error(request, 'Você não tem permissão para excluir a notificação!')
		return JsonResponse({'message': 'not allowed'}, status=400)
	
	try:
		notificacao = Notification.objects.get(pk=notid)

		if notificacao.level != 'communication':
			message = 'Notificação excluida com sucesso!'
		else:
			message = 'Comunicado excluido com sucesso!'
		
		notificacao.delete()
		messages.success(request, message)
		
		return JsonResponse({'message': 'success'}, status=200)
	
	except Exception as e:
		return JsonResponse({'error': e}, status=400)
