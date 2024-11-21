from django.db import models
from django.utils.text import slugify

from django_ckeditor_5.fields import CKEditor5Field
from colorfield.fields import ColorField
from datetime import timedelta

from funcionarios.models import Funcionario


class SolicitacaoFerias(models.Model):
	class Status(models.IntegerChoices):
		ANALISE = 4, 'Em Análise'
		PENDENTE = 3, 'Pendente'
		RECUSADO = 2, 'Recusado'
		APROVADO = 1, 'Aprovado'
		ABERTO = 0, 'Aberto'

	funcionario = models.ForeignKey(Funcionario, on_delete=models.CASCADE, related_name='ferias_funcionario', verbose_name='Funcionário')
	aprovador = models.ForeignKey(Funcionario, on_delete=models.CASCADE, related_name='ferias_aprovador', verbose_name='Aprovador')
	observacao = models.TextField(verbose_name='Observação')
	inicio_periodo = models.DateField(verbose_name='Início Período')
	final_periodo = models.DateField(verbose_name='Final Período')
	inicio_ferias = models.DateField(verbose_name='Início Férias')
	final_ferias = models.DateField(verbose_name='Final Férias')
	abono = models.IntegerField(default=0, verbose_name='Total Abono')
	decimo = models.BooleanField(default=False, verbose_name='13º Salário')
	status = models.IntegerField(choices=Status.choices, default=Status.ABERTO, verbose_name='Status')
	data_cadastro = models.DateTimeField(auto_now_add=True, verbose_name='Data de Cadastro')

	def __str__(self):
		return str(self.funcionario)
	
	@property
	def get_status(self):
		status = [i[1] for i in self.Status.choices if i[0] == self.status]
		return status[0]
	
	class Meta:
		verbose_name = 'Solicitações de Férias'
		verbose_name_plural = 'Solicitação de Férias'


class DocumentosFerias(models.Model):
	solicitacao = models.ForeignKey(SolicitacaoFerias, on_delete=models.CASCADE, verbose_name='Solicitação')
	documento = models.BinaryField(verbose_name='Documento')
	caminho = models.CharField(max_length=256, verbose_name='Caminho do Documento')
	data_cadastro = models.DateTimeField(auto_now_add=True, verbose_name='Data de Cadastro')

	def __str__(self):
		return str(self.documento)

	class Meta:
		verbose_name = 'Documentos de Férias'
		verbose_name_plural = 'Documento de Férias'


class Ferias(models.Model):
	funcionario = models.ForeignKey(Funcionario, on_delete=models.CASCADE, verbose_name='Funcionário')
	ano_referencia = models.IntegerField(verbose_name='Ano de Referência')
	inicio_periodo = models.DateField(verbose_name='Início Período')
	final_periodo = models.DateField(verbose_name='Final Período')
	inicio_ferias = models.DateField(verbose_name='Início Férias')
	final_ferias = models.DateField(verbose_name='Final Férias')
	saldo = models.IntegerField(verbose_name='Saldo do Período')
	abono = models.IntegerField(default=0, verbose_name='Total Abono')
	decimo = models.BooleanField(default=False, verbose_name='13º Salário')
	data_cadastro = models.DateTimeField(auto_now_add=True, verbose_name='Data de Cadastro')

	def save(self, *args, **kwargs):
		if not self.saldo:
			ferias_anterior = Ferias.objects.filter(funcionario=self.funcionario, ano_referencia=self.ano_referencia).order_by('id')
			if ferias_anterior.exists():
				saldo_anterior = (ferias_anterior.last().final_ferias - ferias_anterior.last().inicio_ferias).days
			else:
				saldo_anterior = 15 if self.funcionario.get_contrato.tipo == 'est' else 30
				
			self.saldo = saldo_anterior - (self.final_ferias - self.inicio_ferias).days

		super().save(*args, **kwargs)

	def __str__(self):
		return str(self.funcionario)

	class Meta:
		verbose_name = 'Férias'
		verbose_name_plural = 'Férias'


class TipoAtividade(models.Model):
	tipo = models.CharField(max_length=60, null=False, blank=False, verbose_name='Tipo de Atividade')
	slug = models.SlugField(default='', editable=False, null=True, blank=True, max_length=120)
	cor = ColorField(default='#FF0000')
	data_cadastro = models.DateTimeField(auto_now_add=True, verbose_name='Data de Cadastro')
	avaliativo = models.BooleanField(default=True, verbose_name='Avaliativo')

	def save(self, *args, **kwargs):
		self.tipo = self.tipo.title()
		self.slug = slugify(self.tipo, allow_unicode=False)
		super().save(*args, **kwargs)

	def __str__(self):
		return self.tipo

	class Meta:
		verbose_name = 'Tipo Atividade'
		verbose_name_plural = 'Tipos Atividade'


class Atividade(models.Model):
	titulo = models.CharField(max_length=256, verbose_name='Título')
	descricao = CKEditor5Field('Descrição', config_name='extends')
	tipo = models.ForeignKey(TipoAtividade, on_delete=models.SET_NULL, null=True, blank=True, verbose_name='Tipo')
	recorrencia = models.ForeignKey('Atividade', on_delete=models.SET_NULL, null=True, blank=True, editable=False, verbose_name='Recorrencia')
	inicio = models.DateTimeField(verbose_name='Início da Atividade')
	final = models.DateTimeField(null=True, blank=True, verbose_name='Final da Atividade')
	funcionarios = models.ManyToManyField(Funcionario, verbose_name='Funcionáro')
	data_finalizacao = models.DateTimeField(null=True, blank=True, editable=False, verbose_name='Data de Finalização')
	data_cadastro = models.DateTimeField(auto_now_add=True, verbose_name='Data de Cadastro')
	autor = models.ForeignKey(Funcionario, on_delete=models.CASCADE, editable=False, related_name='autor_atividade')
	solic_ferias = models.ForeignKey(SolicitacaoFerias, on_delete=models.SET_NULL, editable=False, null=True, blank=True)

	def save(self, *args, **kwargs):
		if not self.final:
			self.final = self.inicio + timedelta(days=1)
		super().save(*args, **kwargs)

	def __str__(self):
		return f'{self.tipo} {self.titulo} de {self.autor}'

	class Meta:
		verbose_name = 'Atividade'
		verbose_name_plural = 'Atividades'


class Avaliacao(models.Model):
	# Metodologia 9 box
	# A avaliação 9 box pode ser utilizada a partir de um sistema de gestão de desempenho que permita a sua aplicação.
	# Independentemente da escolha, será preciso criar colunas com critérios que considerem o potencial do colaborador (alto, médio e baixo),
	# alinhadas a outras três colunas sobre seu desempenho (abaixo do esperado, esperado e acima do esperado).

	class Potencial(models.IntegerChoices):
		ALTO = 2, 'Alto'
		MEDIO = 1, 'Medio'
		BAIXO = 0, 'Baixo'

	class Desempenho(models.IntegerChoices):
		ACIMA = 2, 'Acima do Esperado'
		ESPERADO = 1, 'Esperado'
		ABAIXO = 0, 'Abaixo do Esperado'

	atividade = models.ForeignKey(Atividade, on_delete=models.CASCADE, verbose_name='Atividade')
	avaliador = models.ForeignKey(Funcionario, on_delete=models.CASCADE, verbose_name='Avaliador')
	potencial = models.IntegerField(choices=Potencial.choices, default=Potencial.MEDIO, verbose_name='Potencial')
	desempenho = models.IntegerField(choices=Desempenho.choices, default=Desempenho.ESPERADO, verbose_name='Desempenho')
	observacao = CKEditor5Field('Observação', config_name='extends')
	data_cadastro = models.DateTimeField(auto_now_add=True, verbose_name='Data de Cadastro')

	def __str__(self):
		return f'Avaliação da atividade {self.atividade}'

	class Meta:
		verbose_name = 'Desempenho'
		verbose_name_plural = 'Desempenhos'
