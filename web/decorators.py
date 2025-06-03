from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect
from functools import wraps

from datetime import datetime
from time import monotonic

from funcionarios.models import Funcionario
from notifications.models import Notification


def base_context_required(view_func):
	@wraps(view_func)
	@login_required(login_url='entrar')
	def _wrapped_view(request, *args, **kwargs):
		notificacoes = Notification.objects.filter(recipient=request.user, unread=True)
		funcionarios = Funcionario.objects.filter(data_demissao=None).order_by('nome_completo')

		try:
			funcionario = funcionarios.get(usuario=request.user)
		except Funcionario.DoesNotExist:
			messages.warning(request, f'Nenhum funcionário cadastrado para {request.user}!')
			return redirect('admin')

		context = {
			'funcionarios': funcionarios,
			'funcionario': funcionario,
			'notificacoes': notificacoes
		}

		return view_func(request, context, *args, **kwargs)
	
	return _wrapped_view


def record_time(function):
	def wrap(*args, **kwargs):
		start_time = monotonic()
		function_return = function(*args, **kwargs)
		print(f'{datetime.strftime(datetime.today(), "%Y-%m-%d %H:%M:%S.%f")[:-3]} [runserver | INFO] {function.__name__} run time: {(monotonic() - start_time):.3f} seconds')
		return function_return
	return wrap
