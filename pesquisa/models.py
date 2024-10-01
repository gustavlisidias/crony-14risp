from django.db import models

from funcionarios.models import Funcionario


class Pesquisa(models.Model):
	titulo = models.CharField(max_length=256, verbose_name='Título')
	descricao = models.TextField(verbose_name='Descrição')
	funcionarios = models.ManyToManyField(Funcionario, related_name='funcionarios_pesquisa', verbose_name='Funcionários')
	data_cadastro = models.DateTimeField(auto_now_add=True, verbose_name='Data de Cadastro')
	data_encerramento = models.DateTimeField(verbose_name='Data de Encerramento')
	anonimo = models.BooleanField(default=False, verbose_name='Anônimo')

	def __str__(self):
		return self.titulo

	class Meta:
		verbose_name = 'Pesquisa'
		verbose_name_plural = 'Pesquisas'


class Pergunta(models.Model):
	pesquisa = models.ForeignKey(Pesquisa, on_delete=models.CASCADE, verbose_name='Pesquisa')
	texto = models.TextField(verbose_name='Pergunta')
	data_cadastro = models.DateTimeField(auto_now_add=True, verbose_name='Data de Cadastro')
	obrigatorio = models.BooleanField(default=False, verbose_name='Obrigatória')

	def __str__(self):
		return f'Pergunta da pesquisa {self.pesquisa}'

	class Meta:
		verbose_name = 'Pergunta'
		verbose_name_plural = 'Perguntas'


class Resposta(models.Model):
	pergunta = models.ForeignKey(Pergunta, on_delete=models.CASCADE, verbose_name='Pergunta')
	texto = models.TextField(verbose_name='Resposta')
	funcionario = models.ForeignKey(Funcionario, on_delete=models.CASCADE, verbose_name='Funcionário')
	data_cadastro = models.DateTimeField(auto_now_add=True, verbose_name='Data de Cadastro')

	def __str__(self):
		return f'Resposta de {self.funcionario} sobre a {self.pergunta}'

	class Meta:
		verbose_name = 'Resposta'
		verbose_name_plural = 'Respostas'
