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
	funcionarios = Funcionario.objects.filter(data_demissao=None).order_by('nome_completo')
	funcionario = funcionarios.get(usuario=request.user)
	notificacoes = Notification.objects.filter(recipient=request.user, unread=True)

	colaboradores = Funcionario.objects.all()
	comunicados = Notification.objects.all()

	if request.user.get_access == 'common':
		comunicados = comunicados.filter(recipient=request.user)

	if request.user.get_access == 'manager':
		filtro = funcionarios.filter(Q(gerente=funcionario) | Q(pk=funcionario.pk)).distinct().values_list('usuario__id', flat=True)
		comunicados = comunicados.filter(recipient__in=filtro).distinct()

	listagem = []

	for notificacao in comunicados:
		notificacao.remetente = colaboradores.get(usuario__id=int(notificacao.actor_object_id)).nome_completo
		notificacao.destinatario = colaboradores.get(usuario=notificacao.recipient).nome_completo
		
		listagem.append({
			'id': notificacao.id,
			'level': notificacao.level,
			'verb': notificacao.verb,
			'description': notificacao.description,
			'remetente': notificacao.remetente,
			'destinatario': notificacao.destinatario,
			'unread': notificacao.unread,
			'timestamp': notificacao.timestamp.strftime("%d/%m/%Y"),
		})


	context = {
		'funcionarios': funcionarios,
		'funcionario': funcionario,
		'notificacoes': notificacoes,
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
				final=request.POST.get('final')
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
