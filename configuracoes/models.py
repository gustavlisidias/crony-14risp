from slugify import slugify

from django.contrib.auth.models import AbstractBaseUser, PermissionsMixin
from django.core.mail import send_mail
from django.db import models

from configuracoes.manager import GerenciadorUsuario


class Usuario(AbstractBaseUser, PermissionsMixin):
	username = models.CharField(max_length=64, unique=True)
	email = models.EmailField(max_length=128, unique=False, null=True, blank=True)
	first_name = models.CharField(max_length=256)
	last_name = models.CharField(max_length=256)
	is_active = models.BooleanField(default=True)
	is_staff = models.BooleanField(default=False)
	is_superuser = models.BooleanField(default=False)
	is_gerente = models.BooleanField(default=False)
	is_admin = models.BooleanField(default=False)
	is_ouvidor = models.BooleanField(default=False)
	last_login = models.DateTimeField(auto_now=True)
	date_joined = models.DateTimeField(auto_now_add=True)

	objects = GerenciadorUsuario()

	EMAIL_FIELD = 'email'
	USERNAME_FIELD = 'username'
	REQUIRED_FIELDS = ['email']

	def save(self, *args, **kwargs):
		if self.username:
			self.username = slugify(self.username).replace('-', '.')
		if self.first_name:
			self.first_name = self.first_name.title()
		if self.last_name:
			self.last_name = self.last_name.title()
		super().save(*args, **kwargs)

	def __str__(self):
		return self.username
	
	def get_slug_name(self):
		full_name = '%s %s' % (self.first_name, self.last_name)
		return slugify(full_name.strip())

	def get_full_name(self):
		full_name = '%s %s' % (self.first_name, self.last_name)
		return full_name.strip()

	def get_short_name(self):
		return self.first_name

	def email_user(self, subject, message, from_email=None, **kwargs):
		send_mail(subject, message, from_email, [self.email], **kwargs)

	def has_perm(self, perm, obj=None):
		return self.is_active and (self.is_admin or self.is_superuser)

	def has_module_perm(self, app_label):
		return self.is_active and (self.gerente or self.staff)

	@property
	def get_access(self):
		if self.is_active and (self.is_admin or self.is_superuser):
			return 'admin'
		elif self.is_active and (self.is_gerente or self.is_staff):
			return 'manager'
		elif self.is_active:
			return 'common'
		else:
			return None

	class Meta:
		verbose_name = 'Usuário'
		verbose_name_plural = 'Usuários'


class Contrato(models.Model):
	titulo = models.CharField(max_length=60, null=False, blank=False, verbose_name='Contrato')
	descricao = models.CharField(max_length=60, null=False, blank=False, verbose_name='Jornada')
	slug = models.SlugField(default='', editable=False, null=True, blank=True, max_length=120)
	data_cadastro = models.DateTimeField(auto_now_add=True, verbose_name='Data de Cadastro')

	def save(self, *args, **kwargs):
		self.slug = slugify(self.titulo, allow_unicode=False)
		super().save(*args, **kwargs)

	def __str__(self):
		return f'{self.titulo} {self. descricao}'

	class Meta:
		verbose_name = 'Contrato & Jornada'
		verbose_name_plural = 'Contratos & Jornadas'


class Jornada(models.Model):
	class Semana(models.IntegerChoices):
		DOMINGO = 1, 'Domingo'
		SEGUNDA = 2, 'Segunda-feira'
		TERCA = 3, 'Terça-feira'
		QUARTA = 4, 'Quarta-feira'
		QUINTA = 5, 'Quinta-feira'
		SEXTA = 6, 'Sexta-feira'
		SABADO = 7, 'Sábado'

	class Tipo(models.TextChoices):
		ENTRADA = 'E', 'Entrada'
		SAIDA = 'S', 'Saída'

	contrato = models.ForeignKey(Contrato, on_delete=models.CASCADE, verbose_name='Contrato')
	tipo = models.CharField(max_length=1, choices=Tipo.choices, editable=False, verbose_name='Tipo')
	ordem = models.IntegerField(editable=False, verbose_name='Ordem')
	dia = models.IntegerField(choices=Semana.choices, verbose_name='Dia da Semana')
	hora = models.TimeField(verbose_name='Hora')

	def save(self, *args, **kwargs):
		if not self.ordem:
			jornadas = Jornada.objects.filter(contrato=self.contrato, dia=self.dia).order_by('ordem')
			if jornadas.exists():
				self.ordem = jornadas.last().ordem + 1
			else:
				self.ordem = 1

		if not self.tipo:
			if self.ordem % 2 == 1:
				self.tipo = Jornada.Tipo.ENTRADA
			else:
				self.tipo = Jornada.Tipo.SAIDA

		super().save(*args, **kwargs)

	def __str__(self):
		return f'{self.contrato} - {self.get_dia_display()} - {self.hora}'

	class Meta:
		verbose_name = 'Hora Jornada'
		verbose_name_plural = 'Horas Jornadas'


class Variavel(models.Model):
	chave = models.CharField(max_length=256, verbose_name='Chave')
	valor = models.CharField(max_length=512, verbose_name='Valor')

	def __str__(self):
		return f'{self.chave}: {self.valor}'

	class Meta:
		verbose_name = 'Variável'
		verbose_name_plural = 'Variáveis'
