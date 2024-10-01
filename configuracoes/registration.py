from django.contrib import messages
from django.contrib.auth import get_user_model
from django.contrib.auth import login as auth_login
from django.contrib.auth.forms import PasswordResetForm, SetPasswordForm
from django.contrib.auth.tokens import default_token_generator
from django.contrib.auth.views import PasswordContextMixin
from django.core.exceptions import ImproperlyConfigured, ValidationError
from django.http import HttpResponseRedirect
from django.urls import reverse_lazy
from django.utils.decorators import method_decorator
from django.utils.http import urlsafe_base64_decode
from django.views.decorators.cache import never_cache
from django.views.decorators.csrf import csrf_protect
from django.views.decorators.debug import sensitive_post_parameters
from django.views.generic.base import TemplateView
from django.views.generic.edit import FormView


INTERNAL_RESET_SESSION_TOKEN = '_password_reset_token'
UserModel = get_user_model()


class PasswordResetView(PasswordContextMixin, FormView):
	email_template_name = 'autenticacao/recuperar_senha_email.html'
	extra_email_context = None
	form_class = PasswordResetForm
	from_email = None
	html_email_template_name = None
	subject_template_name = 'autenticacao/recuperar_senha_assunto.txt'
	success_url = reverse_lazy('recuperar-senha-enviado')
	template_name = 'autenticacao/recuperar_senha.html'
	title = 'Recuperação de senha'
	token_generator = default_token_generator

	@method_decorator(csrf_protect)
	def dispatch(self, *args, **kwargs):
		return super().dispatch(*args, **kwargs)

	def form_valid(self, form):
		opts = {
			'use_https': self.request.is_secure(),
			'token_generator': self.token_generator,
			'from_email': self.from_email,
			'email_template_name': self.email_template_name,
			'subject_template_name': self.subject_template_name,
			'request': self.request,
			'html_email_template_name': self.html_email_template_name,
			'extra_email_context': self.extra_email_context,
		}
		form.save(**opts)
		return super().form_valid(form)


class PasswordResetDoneView(PasswordContextMixin, TemplateView):
	template_name = 'autenticacao/recuperar_senha_enviado.html'
	title = 'Email de recuperação de senha enviado'


class PasswordResetConfirmView(PasswordContextMixin, FormView):
	form_class = SetPasswordForm
	post_reset_login = False
	post_reset_login_backend = None
	reset_url_token = 'set-password'
	success_url = reverse_lazy('entrar')
	template_name = 'autenticacao/recuperar_senha_alterar.html'
	title = 'Digite sua nova senha'
	token_generator = default_token_generator

	@method_decorator(sensitive_post_parameters())
	@method_decorator(never_cache)
	def dispatch(self, *args, **kwargs):
		if 'uidb64' not in kwargs or 'token' not in kwargs:
			raise ImproperlyConfigured('A URL deve conter os parâmetros de uidb64 e token!')

		self.validlink = False
		self.user = self.get_user(kwargs['uidb64'])

		if self.user is not None:
			token = kwargs['token']
			if token == self.reset_url_token:
				session_token = self.request.session.get(INTERNAL_RESET_SESSION_TOKEN)
				if self.token_generator.check_token(self.user, session_token):
					self.validlink = True
					return super().dispatch(*args, **kwargs)
			else:
				if self.token_generator.check_token(self.user, token):
					self.request.session[INTERNAL_RESET_SESSION_TOKEN] = token
					redirect_url = self.request.path.replace(token, self.reset_url_token)
					return HttpResponseRedirect(redirect_url)

		return self.render_to_response(self.get_context_data())

	def get_user(self, uidb64):
		try:
			uid = urlsafe_base64_decode(uidb64).decode()
			user = UserModel._default_manager.get(pk=uid)

		except (TypeError, ValueError, OverflowError, UserModel.DoesNotExist, ValidationError):
			user = None

		return user

	def get_form_kwargs(self):
		kwargs = super().get_form_kwargs()
		kwargs['user'] = self.user
		return kwargs

	def form_valid(self, form):
		user = form.save()
		del self.request.session[INTERNAL_RESET_SESSION_TOKEN]
		if self.post_reset_login:
			auth_login(self.request, user, self.post_reset_login_backend)

		return super().form_valid(form)

	def form_invalid(self, form):
		messages.error(self.request, 'Erro ao alterar a senha. Por favor, verifique os campos e tente novamente.')
		return super().form_invalid(form)

	def get_context_data(self, **kwargs):
		context = super().get_context_data(**kwargs)
		if self.validlink:
			context['validlink'] = True
		else:
			context.update({'form': None, 'title': 'Erro ao alterar senha', 'validlink': False})
			
		return context
