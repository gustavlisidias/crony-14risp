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


class Nivel(models.Model):
	class Tipo(models.IntegerChoices):
		GESTOR = 2, 'Gestor'
		PAR = 1, 'Par'
		AUTO = 0, 'Auto'

	avaliacao = models.ForeignKey(Avaliacao, on_delete=models.CASCADE, verbose_name='Avaliação')
	tipo = models.IntegerField(choices=Tipo.choices, verbose_name='Tipo de Avaliador')
	peso = models.FloatField(verbose_name='Peso')
	data_cadastro = models.DateTimeField(auto_now_add=True, verbose_name='Data de Cadastro')

	def __str__(self):
		tipo = [i[1] for i in self.Tipo.choices if i[0] == self.tipo][0]
		return f'Nível "{tipo}" com peso {self.peso} para avaliação {self.avaliacao}'

	class Meta:
		verbose_name = 'Nível'
		verbose_name_plural = 'Níveis'


class Pergunta(models.Model):
	titulo = models.CharField(max_length=120, null=False, blank=False, verbose_name='Título')
	texto = CKEditor5Field('Texto', config_name='extends')
	peso = models.FloatField(verbose_name='Peso')
	data_cadastro = models.DateTimeField(auto_now_add=True, verbose_name='Data de Cadastro')

	def __str__(self):
		return f'{self.titulo} (Peso de {self.peso})'

	class Meta:
		verbose_name = 'Pergunta'
		verbose_name_plural = 'Perguntas'


class PerguntaAvaliacao(models.Model):
	pergunta = models.ForeignKey(Pergunta, on_delete=models.CASCADE, verbose_name='Pergunta')
	avaliacao = models.ForeignKey(Avaliacao, on_delete=models.CASCADE, verbose_name='Avaliação')
	data_cadastro = models.DateTimeField(auto_now_add=True, verbose_name='Data de Cadastro')

	def __str__(self):
		return f'{self.pergunta} de {self.avaliacao}'

	class Meta:
		verbose_name = 'Pergunta x Avaliação'
		verbose_name_plural = 'Perguntas x Avaliação'


class Resposta(models.Model):
	referencia = models.ForeignKey(PerguntaAvaliacao, on_delete=models.CASCADE, verbose_name='Pergunta')
	observacao = models.TextField(verbose_name='Observação', null=True, blank=True)
	funcionario = models.ForeignKey(Funcionario, on_delete=models.CASCADE, related_name='reposta_funcionario', verbose_name='Funcionário')
	nota = models.FloatField(verbose_name='Nota')
	data_cadastro = models.DateTimeField(auto_now_add=True, verbose_name='Data de Cadastro')

	def __str__(self):
		return f'Reposta de {self.funcionario} em {self.referencia}'

	class Meta:
		verbose_name = 'Resposta'
		verbose_name_plural = 'Respostas'
