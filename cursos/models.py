import uuid as uid

from django.db import models
from django.db.models.signals import post_save, m2m_changed
from django.dispatch import receiver
from django.utils.text import slugify

from django_ckeditor_5.fields import CKEditor5Field

from configuracoes.models import Contrato
from funcionarios.models import Funcionario


class Curso(models.Model):
	class Tipos(models.TextChoices):
		NDA = 'NDA', 'Nenhum'
		CONC = 'CONC', 'Conclusão'
		PART = 'PART', 'Participação'
	
	titulo = models.CharField(max_length=60, null=False, blank=False, verbose_name='Título')
	descricao = models.TextField(null=False, blank=False, verbose_name='Descrição')
	observacao = models.TextField(null=True, blank=True, verbose_name='Texto Certificado')
	contrato = models.ManyToManyField(Contrato, blank=True, related_name='contratos', verbose_name='Contrato')
	slug = models.SlugField(default='', editable=False, null=True, blank=True, max_length=120)
	tipo = models.CharField(max_length=4, default=Tipos.NDA, choices=Tipos.choices, verbose_name='Tipo de Certificado')
	certificado = models.BooleanField(default=False, verbose_name='Gerar Certificado')
	data_cadastro = models.DateTimeField(auto_now_add=True, verbose_name='Data de Cadastro')

	def save(self, *args, **kwargs):
		self.slug = slugify(self.titulo, allow_unicode=False)
		super().save(*args, **kwargs)

	def __str__(self):
		return self.titulo

	class Meta:
		verbose_name = 'Curso'
		verbose_name_plural = 'Cursos'


class Etapa(models.Model):
	titulo = models.CharField(max_length=60, null=False, blank=False, verbose_name='Título')
	texto = CKEditor5Field('Texto', config_name='extends')
	curso = models.ManyToManyField(Curso, related_name='etapas', verbose_name='Curso')
	data_cadastro = models.DateTimeField(auto_now_add=True, verbose_name='Data de Cadastro')

	def __str__(self):
		return self.titulo

	class Meta:
		verbose_name = 'Etapa'
		verbose_name_plural = 'Etapas'


class CursoFuncionario(models.Model):
	uuid = models.CharField(max_length=255, verbose_name='UUID')
	funcionario = models.ForeignKey(Funcionario, on_delete=models.CASCADE, verbose_name='Funcionário')
	curso = models.ForeignKey(Curso, on_delete=models.CASCADE, verbose_name='Curso')
	data_conclusao = models.DateTimeField(null=True, verbose_name='Data de Conclusão')
	data_cadastro = models.DateTimeField(auto_now_add=True, verbose_name='Data de Cadastro')

	def save(self, *args, **kwargs):
		if not self.uuid:
			self.uuid = uid.uuid4().hex
		if CursoFuncionario.objects.filter(funcionario=self.funcionario, curso=self.curso).exists():
			return
		super().save(*args, **kwargs)

	def __str__(self):
		return f'{self.funcionario.nome_completo} - {self.curso.titulo}'

	class Meta:
		verbose_name = 'Curso por Funcionário'
		verbose_name_plural = 'Cursos por Funcionário'


class ProgressoEtapa(models.Model):
	funcionario = models.ForeignKey(Funcionario, on_delete=models.CASCADE, verbose_name='Funcionário')
	etapa = models.ForeignKey(Etapa, on_delete=models.CASCADE, verbose_name='Etapa')
	data_conclusao = models.DateTimeField(null=True, blank=True, verbose_name='Data de Conclusão')

	def __str__(self):
		return f'{self.funcionario.nome_completo} - {self.etapa.titulo}'

	class Meta:
		verbose_name = 'Progresso de Etapa'
		verbose_name_plural = 'Progresso de Etapas'


# Sempre que um novo registro de CursoFuncionario for salvo, todas as etapas desse curso serão 
# automaticamente criadas em ProgressoEtapa para o funcionário associado
@receiver(post_save, sender=CursoFuncionario)
def criar_etapas_para_curso(sender, instance, created, **kwargs):
	if created:
		curso = instance.curso
		funcionario = instance.funcionario
		etapas_curso = curso.etapas.all()

		for etapa in etapas_curso:
			if not ProgressoEtapa.objects.filter(funcionario=funcionario, etapa=etapa).exists():
				ProgressoEtapa.objects.create(funcionario=funcionario, etapa=etapa)


# Quando uma nova etapa for adicionada à um curso, o sistema automaticamente criará os 
# registros correspondentes em ProgressoEtapa para cada funcionário associado a esse curso
@receiver(m2m_changed, sender=Etapa.curso.through)
def adicionar_progresso_etapa(sender, instance, action, reverse, model, pk_set, **kwargs):
	if action == 'post_add':
		for curso_id in pk_set:
			curso = Curso.objects.get(pk=curso_id)
			funcionarios = CursoFuncionario.objects.filter(curso=curso).values_list('funcionario', flat=True)
			for funcionario_id in funcionarios:
				if not ProgressoEtapa.objects.filter(funcionario_id=funcionario_id, etapa=instance).exists():
					ProgressoEtapa.objects.create(funcionario_id=funcionario_id, etapa=instance)
