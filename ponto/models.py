import re

from django.db import models
from datetime import date

from cities_light.models import Region as Estado
from cities_light.models import SubRegion as Cidade

from funcionarios.models import Funcionario


class Ponto(models.Model):
	funcionario = models.ForeignKey(Funcionario, on_delete=models.CASCADE, related_name='ponto_funcionario', verbose_name='Funcionário')
	data = models.DateField(verbose_name='Data')
	hora = models.TimeField(verbose_name='Hora')
	alterado = models.BooleanField(default=False, verbose_name='Alterado')
	motivo = models.TextField(null=True, blank=True, verbose_name='Motivo')
	encerrado = models.BooleanField(default=False, verbose_name='Encerrado')
	data_fechamento = models.DateField(blank=True, null=True, verbose_name='Data Fechamento')
	autor_modificacao = models.ForeignKey(Funcionario, on_delete=models.CASCADE, related_name='ponto_autor', editable=False, verbose_name='Autor da Modificação')
	data_modificacao = models.DateTimeField(auto_now_add=True, null=True, editable=False, verbose_name='Data de Modificação')

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
	
	class Categoria(models.TextChoices):
		PERIODO = 'P', 'Período'
		TEMPO = 'T', 'Tempo Faltante'

	def upload(instance, filename):
		caminho = 'documentos/{matricula}/{filename}'.format(matricula=(instance.funcionario.matricula), filename=re.sub('[^A-Za-z0-9.]+', '', filename))
		return caminho

	funcionario = models.ForeignKey(Funcionario, on_delete=models.CASCADE, related_name='abono_funcionario', verbose_name='Funcionário')
	aprovador = models.ForeignKey(Funcionario, on_delete=models.CASCADE, null=True, blank=True, related_name='abono_aprovador', verbose_name='Aprovador')
	inicio = models.DateTimeField(verbose_name='Data Inicial')
	final = models.DateTimeField(null=True, blank=True, verbose_name='Data Final')
	tipo = models.CharField(max_length=2, choices=Tipo.choices, verbose_name='Tipo')
	categoria = models.CharField(max_length=1, choices=Categoria.choices, default=Categoria.PERIODO, verbose_name='Categoria')
	motivo = models.TextField(verbose_name='Motivo')
	documento = models.BinaryField(null=True, blank=True, verbose_name='Documento')
	caminho = models.CharField(max_length=256, null=True, blank=True, verbose_name='Caminho do Documento')
	status = models.BooleanField(default=False, verbose_name='Aprovado')
	data_cadastro = models.DateTimeField(auto_now_add=True, verbose_name='Data de Cadastro')

	def __str__(self):
		return f'Solicitação de abono de {self.funcionario} em {self.inicio.date()}'
	
	@property
	def get_tipo(self):
		tipo = [i[1] for i in self.Tipo.choices if i[0] == self.tipo][0]
		return tipo

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
	class Regiao(models.TextChoices):
		NACIONAL = 'NA', 'Nacional'
		ESTADUAL = 'ES', 'Estadual'
		MUNICIPAL = 'MU', 'Municipal'

	titulo = models.CharField(max_length=256, verbose_name='Título')
	data = models.DateField(verbose_name='Data Feriado')
	regiao = models.CharField(max_length=2, choices=Regiao.choices, default='NA', verbose_name='Região')
	estado = models.ForeignKey(Estado, on_delete=models.CASCADE, null=True, verbose_name='Estado')
	cidade = models.ForeignKey(Cidade, on_delete=models.CASCADE, null=True, verbose_name='Cidade')
	data_cadastro = models.DateTimeField(auto_now_add=True, verbose_name='Data de Cadastro')

	def __str__(self):
		return f'{self.titulo} - {self.data}'
	
	def get_feriado_funcionario(self, funcionario):
		if self.regiao == self.Regiao.NACIONAL:
			return True
		elif self.regiao == self.Regiao.ESTADUAL and funcionario.estado == self.estado:
			return True
		elif self.regiao == self.Regiao.MUNICIPAL and funcionario.estado == self.estado and funcionario.cidade == self.cidade:
			return True
		return False

	class Meta:
		verbose_name = 'Feriado'
		verbose_name_plural = 'Feriados'


class Fechamento(models.Model):
	funcionario = models.ForeignKey(Funcionario, on_delete=models.CASCADE, verbose_name='Funcionário')
	pontuacao = models.FloatField(default=0, verbose_name='Pontuação Assiduidade')
	moedas = models.FloatField(default=1, verbose_name='Moedas')
	referencia = models.PositiveIntegerField(editable=False, verbose_name='Referência Ano-Mês')
	data_cadastro = models.DateTimeField(auto_now_add=True, verbose_name='Data de Cadastro')

	def save(self, *args, **kwargs):
		if not self.referencia:
			self.referencia = int(date.today().strftime('%Y%m'))
		super().save(*args, **kwargs)

	def __str__(self):
		return f'Fechamento de {self.funcionario} - {self.referencia}'
	
	class Meta:
		verbose_name = 'Fechamentos'
		verbose_name_plural = 'Fechamentos'
