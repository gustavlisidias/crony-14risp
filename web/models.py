import pytz

from django.contrib.contenttypes.fields import GenericForeignKey, GenericRelation
from django.contrib.contenttypes.models import ContentType
from django.db import models
from django.utils.text import slugify

from datetime import datetime

from django_ckeditor_5.fields import CKEditor5Field
from funcionarios.models import Funcionario


class Postagem(models.Model):
	titulo = models.CharField(max_length=100, verbose_name='Título')
	texto = CKEditor5Field('Texto', config_name='extends')
	funcionario = models.ForeignKey(Funcionario, on_delete=models.CASCADE, verbose_name='Funcionário')
	slug = models.SlugField(default='', editable=False, null=True, blank=True, max_length=120)
	curtidas = GenericRelation('Curtida')
	comentarios = GenericRelation('Comentario')
	data_cadastro = models.DateTimeField(auto_now_add=True, verbose_name='Data de Cadastro')

	def save(self, *args, **kwargs):
		self.slug = slugify(self.titulo, allow_unicode=False)
		super().save(*args, **kwargs)

	def __str__(self):
		return self.titulo

	class Meta:
		verbose_name = 'Postagem'
		verbose_name_plural = 'Postagens'


class Celebracao(models.Model):
	titulo = models.CharField(max_length=100, verbose_name='Título')
	texto = models.TextField(verbose_name='Celebração')
	celebrante = models.ForeignKey(Funcionario, on_delete=models.SET_NULL, null=True, blank=True, related_name='funcionario_celebrante', verbose_name='Celebrante')
	funcionario = models.ManyToManyField(Funcionario, related_name='funcionario_celebracao', verbose_name='Funcionários')
	data_celebracao = models.DateField(verbose_name='Data da Celebração')
	curtidas = GenericRelation('Curtida')
	comentarios = GenericRelation('Comentario')
	data_cadastro = models.DateTimeField(auto_now_add=True, verbose_name='Data de Cadastro')

	def __str__(self):
		return self.titulo

	class Meta:
		verbose_name = 'Celebração'
		verbose_name_plural = 'Celebrações'


class Curtida(models.Model):
	content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE)
	object_id = models.PositiveIntegerField()
	content_object = GenericForeignKey('content_type', 'object_id')
	funcionario = models.ForeignKey(Funcionario, on_delete=models.CASCADE, verbose_name='Funcionário')
	data_cadastro = models.DateTimeField(auto_now_add=True, verbose_name='Data de Cadastro')

	def __str__(self):
		return f'Curtida de {self.funcionario} em {self.content_object}'

	class Meta:
		verbose_name = 'Curtida'
		verbose_name_plural = 'Curtidas'


class Comentario(models.Model):
	content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE)
	object_id = models.PositiveIntegerField()
	content_object = GenericForeignKey('content_type', 'object_id')
	funcionario = models.ForeignKey(Funcionario, on_delete=models.CASCADE, verbose_name='Funcionário')
	comentario = models.TextField(verbose_name='Comentário')
	data_cadastro = models.DateTimeField(auto_now_add=True, verbose_name='Data de Cadastro')

	def __str__(self):
		return f'Comentário de {self.funcionario} em {self.content_object}'

	class Meta:
		verbose_name = 'Comentário'
		verbose_name_plural = 'Comentários'


class Humor(models.Model):
	class Status(models.TextChoices):
		FELIZ = '5', 'Muito Feliz'
		ALEGRE = '4', 'Feliz'
		NEUTRO = '3', 'Neutro'
		CHATEADO = '2', 'Triste'
		TRISTE = '1', 'Muito Triste'

	humor = models.CharField(max_length=1, choices=Status.choices, verbose_name='Humor')
	funcionario = models.ForeignKey(Funcionario, on_delete=models.CASCADE, verbose_name='Funcionário')
	data_cadastro = models.DateTimeField(auto_now_add=True, verbose_name='Data de Cadastro')

	def __str__(self):
		return f'{self.funcionario} estava com o humor: {self.get_humor_display()}'

	class Meta:
		verbose_name = 'Humor'
		verbose_name_plural = 'Humores'


class Ouvidoria(models.Model):
	class Status(models.IntegerChoices):
		ABERTO = 1, 'Aberto'
		FECHADO = 2, 'Fechado'
		PENDENTE = 3, 'Pendente'

	class Categoria(models.IntegerChoices):
		RECLAMACAO = 1, 'Reclamação'
		SUGESTAO = 2, 'Sugestão'
		DENUNCIA = 3, 'Denuncia'

	funcionario = models.ForeignKey(Funcionario, related_name='ouvidoria_funcionario', on_delete=models.CASCADE)
	responsavel = models.ForeignKey(Funcionario, related_name='ouvidoria_responsavel', null=True, blank=True, on_delete=models.SET_NULL)
	categoria = models.IntegerField(choices=Categoria.choices, default=1)
	assunto = models.CharField(max_length=255)
	descricao = CKEditor5Field('Descrição', config_name='extends')
	status = models.IntegerField(choices=Status.choices, default=1)
	anonimo = models.BooleanField(default=True, verbose_name='Anônimo')
	data_cadastro = models.DateTimeField(auto_now_add=True, verbose_name='Data de Cadastro')

	def __str__(self):
		return f'Ouvidoria #{self.id} - {self.assunto}'

	class Meta:
		verbose_name = 'Ouvidoria'
		verbose_name_plural = 'Ouvidoria'


class MensagemOuvidoria(models.Model):
	ticket = models.ForeignKey(Ouvidoria, related_name='mensagens', on_delete=models.CASCADE)
	remetente = models.ForeignKey(Funcionario, on_delete=models.CASCADE)
	mensagem = CKEditor5Field('Mensagem', config_name='extends')
	data_cadastro = models.DateTimeField(auto_now_add=True, verbose_name='Data de Cadastro')
	
	def __str__(self):
		return f'Mensagem #{self.id} na Ouvidoria #{self.ticket.id}'

	class Meta:
		verbose_name = 'Mensagem Ouvidoria'
		verbose_name_plural = 'Mensagens Ouvidoria'


class Moeda(models.Model):
	funcionario = models.ForeignKey(Funcionario, on_delete=models.CASCADE, verbose_name='Funcionário')
	pontuacao = models.FloatField(default=0, verbose_name='Pontuação')
	fechado = models.BooleanField(default=False, verbose_name='Fechado')
	anomes = models.PositiveIntegerField(editable=False, verbose_name='Referência Ano Mês')
	data_cadastro = models.DateTimeField(auto_now=True, verbose_name='Data de Cadastro')

	def save(self, *args, **kwargs):
		if not self.data_cadastro:
			self.data_cadastro = datetime.now().replace(tzinfo=pytz.utc)
		self.anomes = int(self.data_cadastro.strftime('%Y%m'))
		super().save(*args, **kwargs)

	def __str__(self):
		return f'{self.funcionario.nome_completo} têm {self.pontuacao} em {self.data_cadastro}'

	class Meta:
		unique_together = ('funcionario', 'anomes', 'fechado')
		verbose_name = 'Moeda'
		verbose_name_plural = 'Moedas'
