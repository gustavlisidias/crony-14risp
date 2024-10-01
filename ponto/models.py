import re

from django.db import models

from funcionarios.models import Funcionario


class Ponto(models.Model):
	funcionario = models.ForeignKey(Funcionario, on_delete=models.CASCADE, verbose_name='Funcionário')
	data = models.DateField(verbose_name='Data')
	hora = models.TimeField(verbose_name='Hora')
	alterado = models.BooleanField(default=False, verbose_name='Alterado')
	motivo = models.TextField(null=True, blank=True, verbose_name='Motivo')
	encerrado = models.BooleanField(default=False, verbose_name='Encerrado')
	data_fechamento = models.DateField(blank=True, null=True, verbose_name='Encerrado')

	def __str__(self):
		return f'{self.funcionario} em {self.data} as {self.hora}'

	class Meta:
		verbose_name = 'Ponto de Horas'
		verbose_name_plural = 'Ponto de Horas'


class SolicitacaoPonto(models.Model):
	funcionario = models.ForeignKey(Funcionario, on_delete=models.CASCADE, related_name='solicitacao_funcionario', verbose_name='Funcionário')
	aprovador = models.ForeignKey(Funcionario, on_delete=models.CASCADE, null=True, blank=True, related_name='solicitacao_aprovador', verbose_name='Aprovador')
	data = models.DateField(verbose_name='Data')
	hora = models.TimeField(verbose_name='Hora')
	motivo = models.TextField(verbose_name='Motivo')
	status = models.BooleanField(default=False, verbose_name='Aprovado')
	data_cadastro = models.DateTimeField(auto_now_add=True, verbose_name='Data de Cadastro')

	def __str__(self):
		return f'{self.funcionario} em {self.data} as {self.hora}'

	class Meta:
		verbose_name = 'Solicitações de Ajuste'
		verbose_name_plural = 'Solicitação de Ajuste'


class SolicitacaoAbono(models.Model):
	class Tipo(models.TextChoices):
		ATESTADO = 'AT', 'Atestado'
		AUSENCIA = 'AJ', 'Ausência Justificada'
		DECLARACAO = 'DC', 'Declaração'
		FALTA = 'FT', 'Falta'

	def upload(instance, filename):
		caminho = 'documentos/{matricula}/{filename}'.format(matricula=(instance.funcionario.matricula), filename=re.sub('[^A-Za-z0-9.]+', '', filename))
		return caminho

	funcionario = models.ForeignKey(Funcionario, on_delete=models.CASCADE, related_name='abono_funcionario', verbose_name='Funcionário')
	aprovador = models.ForeignKey(Funcionario, on_delete=models.CASCADE, null=True, blank=True, related_name='abono_aprovador', verbose_name='Aprovador')
	inicio = models.DateTimeField(verbose_name='Data Inicial')
	final = models.DateTimeField(verbose_name='Data Final')
	tipo = models.CharField(max_length=2, choices=Tipo.choices, verbose_name='Tipo')
	motivo = models.TextField(verbose_name='Motivo')
	documento = models.BinaryField(null=True, blank=True, verbose_name='Documento')
	caminho = models.CharField(max_length=256, null=True, blank=True, verbose_name='Caminho do Documento')
	status = models.BooleanField(default=False, verbose_name='Aprovado')
	data_cadastro = models.DateTimeField(auto_now_add=True, verbose_name='Data de Cadastro')

	def __str__(self):
		return f'Solicitação de abono de {self.funcionario} em {self.inicio.date()}'

	class Meta:
		verbose_name = 'Solicitações de Abono'
		verbose_name_plural = 'Solicitação de Abono'


class Saldos(models.Model):
	funcionario = models.ForeignKey(Funcionario, on_delete=models.CASCADE, verbose_name='Funcionário')
	saldo = models.DurationField(verbose_name='Saldo', help_text='Formato: DD hh:mm:ss')
	data = models.DateField(verbose_name='Data')
	data_cadastro = models.DateTimeField(auto_now_add=True, verbose_name='Data de Cadastro')

	def __str__(self):
		return f'{self.funcionario.nome_completo} tem {self.saldo} a partir de {self.data}'

	class Meta:
		verbose_name = 'Saldo'
		verbose_name_plural = 'Saldos'


class Feriados(models.Model):
	funcionarios = models.ManyToManyField(Funcionario, related_name='funcionarios_feriados', verbose_name='Funcionários')
	titulo = models.CharField(max_length=256, verbose_name='Título')
	data = models.DateField(verbose_name='Data')
	status = models.BooleanField(default=False, verbose_name='Status')
	data_cadastro = models.DateTimeField(auto_now_add=True, verbose_name='Data de Cadastro')

	def __str__(self):
		return self.titulo

	class Meta:
		verbose_name = 'Feriado'
		verbose_name_plural = 'Feriados'
