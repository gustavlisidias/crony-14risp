import uuid as uid

from django.db import models

from datetime import datetime

from funcionarios.models import Funcionario


class Sala(models.Model):
	class Tipos(models.TextChoices):
		GRUPO = 'G', 'Grupo'
		CONVERSA = 'C', 'Conversa Privada'

	uuid = models.CharField(max_length=255, null=True, blank=True, verbose_name='UUID')
	nome = models.CharField(max_length=255, null=True, blank=True, verbose_name='Nome da Sala')
	tipo = models.CharField(max_length=1, choices=Tipos.choices, default=Tipos.CONVERSA, verbose_name='Tipo de Sala')
	funcionarios = models.ManyToManyField(Funcionario, related_name='salas', blank=True, verbose_name='Funcionários')
	data_modificacao = models.DateTimeField(auto_now=True, verbose_name='Data de Modificação')
	data_cadastro = models.DateTimeField(auto_now_add=True, verbose_name='Data de Cadastro')

	def save(self, *args, **kwargs):
		if not self.uuid:
			self.uuid = uid.uuid4().hex
		super().save(*args, **kwargs)

	def __str__(self):
		if self.nome:
			return f'{self.tipo}: {self.nome}'
		return f'{self.tipo}: {self.uuid}'
	
	class Meta:
		verbose_name = 'Sala'
		verbose_name_plural = 'Salas'
	

class Mensagem(models.Model):
	sala = models.ForeignKey(Sala, on_delete=models.CASCADE, related_name='mensagens_sala', verbose_name='Sala')
	remetente = models.ForeignKey(Funcionario, on_delete=models.CASCADE, related_name='mensagens_remetente', verbose_name='Rementente')
	mensagem = models.TextField(verbose_name='Mensagem')
	text_respondido = models.TextField(null=True, blank=True, verbose_name='Respondido do Texto')
	nome_respondido = models.CharField(max_length=256, null=True, blank=True, verbose_name='Respondido do Usuário')
	lido = models.BooleanField(default=False, verbose_name='Lido')
	data_cadastro = models.DateTimeField(auto_now_add=True, verbose_name='Data de Cadastro')

	def save(self, *args, **kwargs):
		self.sala.data_modificacao = datetime.now()
		super().save(*args, **kwargs)

	def __str__(self):
		return self.remetente.nome_completo
	
	class Meta:
		verbose_name = 'Mensagem'
		verbose_name_plural = 'Mensagens'


class Arquivo(models.Model):
	sala = models.ForeignKey(Sala, on_delete=models.CASCADE, related_name='arquivos_sala', verbose_name='Sala')
	remetente = models.ForeignKey(Funcionario, on_delete=models.CASCADE, related_name='arquivos_rementente', verbose_name='Remetente')
	arquivo = models.FileField(upload_to='chat/', verbose_name='Arquivo')
	text_respondido = models.TextField(null=True, blank=True, verbose_name='Respondido do Texto')
	nome_respondido = models.CharField(max_length=256, null=True, blank=True, verbose_name='Respondido do Usuário')
	lido = models.BooleanField(default=False, verbose_name='Lido')
	data_cadastro = models.DateTimeField(auto_now_add=True, verbose_name='Data de Cadastro')

	def save(self, *args, **kwargs):
		self.sala.data_modificacao = datetime.now()
		super().save(*args, **kwargs)

	def __str__(self):
		return f'{self.remetente.nome_completo} enviou o arquivo: {self.arquivo}'
	
	class Meta:
		verbose_name = 'Arquivo'
		verbose_name_plural = 'Arquivos'
