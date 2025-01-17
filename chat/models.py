import uuid as uid

from django.db import models

from funcionarios.models import Funcionario


class Sala(models.Model):
	class Tipos(models.TextChoices):
		GRUPO = 'G', 'Grupo'
		CONVERSA = 'C', 'Conversa Privada'

	uuid = models.CharField(max_length=255, null=True, blank=True, verbose_name='UUID')
	nome = models.CharField(max_length=255, null=True, blank=True, verbose_name='Nome da Sala')
	tipo = models.CharField(max_length=1, choices=Tipos.choices, default=Tipos.CONVERSA, verbose_name='Tipo de Sala')
	funcionarios = models.ManyToManyField(Funcionario, related_name='salas', blank=True, verbose_name='Funcionários')
	data_cadastro = models.DateTimeField(auto_now_add=True, verbose_name='Data de Cadastro')

	def save(self, *args, **kwargs):
		if not self.uuid:
			self.uuid = uid.uuid4().hex
		super().save(*args, **kwargs)

	def __str__(self):
		if self.nome:
			return f'{self.tipo}: {self.nome}'
		return f'{self.tipo}: {self.uuid}'
	

class Mensagem(models.Model):
	sala = models.ForeignKey(Sala, on_delete=models.CASCADE, related_name='mensagens_sala', verbose_name='Sala')
	remetente = models.ForeignKey(Funcionario, on_delete=models.CASCADE, related_name='mensagens_remetente', verbose_name='Rementente')
	mensagem = models.TextField(verbose_name='Mensagem')
	lido = models.BooleanField(default=False, verbose_name='Lido')
	data_cadastro = models.DateTimeField(auto_now_add=True, verbose_name='Data de Cadastro')

	def __str__(self):
		return f'{self.remetente.nome_completo} enviou a mensagem: {self.mensagem}'


class Arquivo(models.Model):
	sala = models.ForeignKey(Sala, on_delete=models.CASCADE, related_name='arquivos_sala', verbose_name='Sala')
	remetente = models.ForeignKey(Funcionario, on_delete=models.CASCADE, related_name='arquivos_rementente', verbose_name='Remetente')
	arquivo = models.FileField(upload_to='chat/', verbose_name='Arquivo')
	lido = models.BooleanField(default=False, verbose_name='Lido')
	data_cadastro = models.DateTimeField(auto_now_add=True, verbose_name='Data de Cadastro')

	def __str__(self):
		return f'{self.remetente.username} enviou o arquivo: {self.arquivo}'
