from django.db import models
from django.utils.text import slugify

from django_ckeditor_5.fields import CKEditor5Field

from funcionarios.models import Funcionario


class Avaliacao(models.Model):
	titulo = models.CharField(max_length=120, null=False, blank=False, verbose_name='Título')
	descricao = CKEditor5Field('Descrição', config_name='extends')
	inicio = models.DateField(verbose_name='Início')
	final = models.DateField(verbose_name='Final')
	status = models.BooleanField(default=False, verbose_name='Fechado')
	slug = models.SlugField(default='', editable=False, null=True, blank=True, max_length=240)
	avaliado = models.ForeignKey(Funcionario, on_delete=models.SET_NULL, null=True, related_name='avaliado_avaliacao', verbose_name='Avaliado')
	avaliadores = models.ManyToManyField(Funcionario, related_name='avaliadores_avaliacao', verbose_name='Avaliadores')
	data_encerramento = models.DateField(verbose_name='Data de Encerramento')
	data_cadastro = models.DateTimeField(auto_now_add=True, verbose_name='Data de Cadastro')

	def save(self, *args, **kwargs):
		self.titulo = self.titulo.title()
		self.slug = slugify(self.titulo, allow_unicode=False)
		super().save(*args, **kwargs)

	def __str__(self):
		return self.titulo

	class Meta:
		verbose_name = 'Avaliação'
		verbose_name_plural = 'Avaliações'


class Criterio(models.Model):
	nome = models.CharField(max_length=120, null=False, blank=False, verbose_name='Nome')
	slug = models.SlugField(default='', editable=False, null=True, blank=True, max_length=240)
	data_cadastro = models.DateTimeField(auto_now_add=True, verbose_name='Data de Cadastro')

	def save(self, *args, **kwargs):
		self.slug = slugify(self.nome, allow_unicode=False)
		super().save(*args, **kwargs)

	def __str__(self):
		return self.nome

	class Meta:
		verbose_name = 'Critério'
		verbose_name_plural = 'Critérios'


class Pergunta(models.Model):
	titulo = models.CharField(max_length=120, null=False, blank=False, verbose_name='Título')
	texto = CKEditor5Field('Texto', config_name='extends')
	data_cadastro = models.DateTimeField(auto_now_add=True, verbose_name='Data de Cadastro')

	def __str__(self):
		return self.titulo

	class Meta:
		verbose_name = 'Pergunta'
		verbose_name_plural = 'Perguntas'


class PesoCriterio(models.Model):
	avaliacao = models.ForeignKey(Avaliacao, on_delete=models.CASCADE, verbose_name='Avaliação')
	pergunta = models.ForeignKey(Pergunta, on_delete=models.CASCADE, verbose_name='Pergunta')
	criterio = models.ForeignKey(Criterio, on_delete=models.CASCADE, verbose_name='Critério')
	peso = models.FloatField(verbose_name='Peso')

	def __str__(self):
		return f'{self.avaliacao} - {self.pergunta} - {self.criterio}'

	class Meta:
		verbose_name = 'Pergunta por Avaliação'
		verbose_name_plural = 'Perguntas por Avaliação'


class PesoAvaliador(models.Model):
	class Nivel(models.IntegerChoices):
		GESTOR = 2, 'Gestor'
		PAR = 1, 'Par'
		AUTO = 0, 'Auto'

	avaliacao = models.ForeignKey(Avaliacao, on_delete=models.CASCADE, verbose_name='Avaliação')
	nivel = models.IntegerField(choices=Nivel.choices, verbose_name='Nível')
	peso = models.FloatField(verbose_name='Peso')

	def __str__(self):
		return f'{self.avaliacao} - {self.nivel}'

	class Meta:
		verbose_name = 'Nível por Avaliação'
		verbose_name_plural = 'Níveis por Avaliação'


class Resposta(models.Model):
	pergunta = models.ForeignKey(PesoCriterio, on_delete=models.CASCADE, verbose_name='Pergunta')
	nota = models.FloatField(verbose_name='Nota')
	observacao = models.TextField(verbose_name='Observação')
	funcionario = models.ForeignKey(Funcionario, on_delete=models.CASCADE, related_name='funcionario_reposta_avaliacao', verbose_name='Funcionário')
	data_cadastro = models.DateTimeField(auto_now_add=True, verbose_name='Data de Cadastro')

	def __str__(self):
		return f'Reposta de {self.funcionario} - {self.pergunta}'

	class Meta:
		verbose_name = 'Resposta'
		verbose_name_plural = 'Respostas'
