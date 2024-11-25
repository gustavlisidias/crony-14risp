from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Q
from django.http import HttpResponseRedirect, JsonResponse
from django.shortcuts import render, redirect

from agenda.models import Atividade, TipoAtividade
from funcionarios.models import Funcionario
from notifications.models import Notification
from web.utils import not_none_not_empty


# Page
@login_required(login_url='entrar')
def NotificacoesView(request):
	funcionarios = Funcionario.objects.all()
	funcionario = funcionarios.get(usuario=request.user)

	if request.user.get_access == 'common':
		users = [request.user.id]
	elif request.user.get_access == 'manager':
		users = [j.usuario.id for j in funcionarios.filter(data_demissao=None).filter(Q(gerente=funcionario) | Q(pk=funcionario.pk)).distinct()]
	else:
		users = [i.usuario.id for i in funcionarios]

	comunicados = Notification.objects.filter(recipient__id__in=users).values('id', 'level', 'verb', 'description', 'unread', 'timestamp', 'recipient__id', 'actor_object_id')
	nomes = [{'nome': i.nome_completo, 'user_id': i.usuario.id} for i in funcionarios]
	listagem = []

	for comunicado in comunicados:
		remetente = [i['nome'] for i in nomes if i['user_id'] == int(comunicado['actor_object_id'])]
		destinatario = [i['nome'] for i in nomes if i['user_id'] == int(comunicado['recipient__id'])]
		
		listagem.append({
			'id': comunicado['id'],
			'level': comunicado['level'],
			'verb': comunicado['verb'],
			'description': comunicado['description'],
			'remetente': remetente[0] if remetente else None,
			'destinatario': destinatario[0] if destinatario else None,
			'unread': comunicado['unread'],
			'timestamp': comunicado['timestamp'].strftime('%d/%m/%Y'),
		})

	context = {
		'funcionarios': funcionarios.filter(data_demissao=None).order_by('nome_completo'),
		'funcionario': funcionario,
		'listagem': listagem,
	}
	return render(request, 'pages/notificacoes.html', context)


# Modal
@login_required(login_url='entrar')
def EditarNotificacaoView(request, notid):
	if not request.method == 'POST':
		messages.warning(request, 'Método não permitido!')
		return redirect('notificacoes')
	
	if request.user.get_access != 'admin':
		messages.error(request, 'Você não tem permissão para adicionar uma notificação!')
		return redirect('notificacoes')

	try:
		notificacao = Notification.objects.get(pk=notid)
		Notification.objects.filter(verb=notificacao.verb, description=notificacao.description, level=notificacao.level, actor_object_id=notificacao.actor_object_id).update(
			verb=request.POST.get('titulo'),
			description=request.POST.get('descricao')
		)
		messages.success(request, 'Notificação alterada com sucesso!')

	except Exception as e:
		messages.error(request, f'Notificação não foi alterada: {e}!')
	
	return HttpResponseRedirect(request.META.get('HTTP_REFERER', '/'))


# Modal
@login_required(login_url='entrar')
def AdicionarNotificacaoView(request):
	if not request.method == 'POST':
		messages.warning(request, 'Método não permitido!')
		return JsonResponse({'message': 'forbidden'}, status=404)

	if request.user.get_access != 'admin':
		messages.error(request, 'Você não tem permissão para adicionar uma notificação!')
		return JsonResponse({'message': 'not allowed'}, status=400)

	assunto = request.POST.get('assunto')
	descricao = request.POST.get('descricao')
	funcinarios = request.POST.getlist('usuarios')
	tipo = request.POST.getlist('level')
	agendamento = request.POST.get('agendamento')

	if not_none_not_empty(assunto, descricao, funcinarios, tipo):
		if not_none_not_empty(agendamento):
			atividade = Atividade.objects.create(
				titulo=assunto,
				descricao=descricao,
				tipo=TipoAtividade.objects.get(slug='comunicado'),
				inicio=request.POST.get('inicio'),
				final=request.POST.get('final'),
				autor=Funcionario.objects.get(usuario=request.user)
			)

			atividade.funcionarios.set(funcinarios)

		for uid in funcinarios:
			if tipo == 'notificacao':
				Notification(
					recipient=Funcionario.objects.get(pk=uid).usuario,
					actor=request.user,
					verb=assunto,
					description=descricao,
				).save()
				messages.success(request, 'Notificação criada com sucesso!')

			else:
				Notification(
					recipient=Funcionario.objects.get(pk=uid).usuario,
					actor=request.user,
					verb=assunto,
					description=descricao,
					level='communication'
				).save()
				messages.success(request, 'Comunicado criado com sucesso!')

	return HttpResponseRedirect(request.META.get('HTTP_REFERER', '/'))
