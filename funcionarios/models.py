import re
import pytz

from django.db import models
from django.utils.text import slugify

from datetime import datetime, date
from colorfield.fields import ColorField
from django_ckeditor_5.fields import CKEditor5Field

from cities_light.models import Region as Estado
from cities_light.models import SubRegion as Cidade
from configuracoes.models import Contrato, Jornada, Usuario
from web.utils import not_none_not_empty


class Setor(models.Model):
	setor = models.CharField(max_length=60, null=False, blank=False, verbose_name='Setor')
	slug = models.SlugField(default='', editable=False, null=True, blank=True, max_length=120)
	responsavel = models.ForeignKey('Funcionario', on_delete=models.SET_NULL, null=True, related_name='responsavel_setor_set', verbose_name='Responsável')
	data_cadastro = models.DateTimeField(auto_now_add=True, verbose_name='Data de Cadastro')

	def save(self, *args, **kwargs):
		self.setor = self.setor.title()
		self.slug = slugify(self.setor, allow_unicode=False)
		super().save(*args, **kwargs)

	def __str__(self):
		return self.setor

	class Meta:
		verbose_name = 'Setor'
		verbose_name_plural = 'Setores'


class Cargo(models.Model):
	cargo = models.CharField(max_length=60, null=False, blank=False, verbose_name='Cargo')
	slug = models.SlugField(default='', editable=False, null=True, blank=True, max_length=120)
	data_cadastro = models.DateTimeField(auto_now_add=True, verbose_name='Data de Cadastro')

	def save(self, *args, **kwargs):
		self.cargo = self.cargo.title()
		self.slug = slugify(self.cargo, allow_unicode=False)
		super().save(*args, **kwargs)

	def __str__(self):
		return self.cargo

	class Meta:
		verbose_name = 'Cargo'
		verbose_name_plural = 'Cargos'


class Funcionario(models.Model):
	class Sexo(models.TextChoices):
		MASCULINO = 'M', 'Masculino'
		FEMININO = 'F', 'Feminino'

	class Estados(models.TextChoices):
		SOLTEIRO = 'S', 'Solteiro (a)'
		CASADO = 'C', 'Casado (a)'
		DIVORCIADO = 'D', 'Divorciado (a)'
		VIUVO = 'V', 'Viúvo (a)'
		UNIAO = 'U', 'União Estável'

	usuario = models.OneToOneField(Usuario, on_delete=models.CASCADE, verbose_name='Usuário')
	matricula = models.CharField(max_length=32, null=True, blank=True, unique=True, verbose_name='Matrícula')
	nome_completo = models.CharField(max_length=256, null=True, blank=True, verbose_name='Nome Completo')
	nome_social = models.CharField(max_length=256, null=True, blank=True, verbose_name='Nome Social')
	nome_mae = models.CharField(max_length=256, null=True, blank=True, verbose_name='Nome da Mãe')
	nome_pai = models.CharField(max_length=256, null=True, blank=True, verbose_name='Nome do Pai')
	email = models.CharField(max_length=64, null=True, blank=True, verbose_name='Email')
	email_sec = models.CharField(max_length=64, null=True, blank=True, verbose_name='Email Secundário')
	contato = models.CharField(max_length=16, null=True, blank=True, verbose_name='Contato')
	contato_sec = models.CharField(max_length=16, null=True, blank=True, verbose_name='Contato Secundário')
	resp_contato_sec = models.CharField(max_length=64, null=True, blank=True, verbose_name='Responsável Contato Secundário')
	cpf = models.CharField(max_length=16, null=True, blank=True, verbose_name='CPF')
	rg = models.CharField(max_length=16, null=True, blank=True, verbose_name='RG')
	sexo = models.CharField(max_length=1, choices=Sexo.choices, default=Sexo.MASCULINO, verbose_name='Sexo')
	estado_civil = models.CharField(max_length=1, choices=Estados.choices, default=Estados.SOLTEIRO, verbose_name='Estado Civil')
	estado = models.ForeignKey(Estado, on_delete=models.CASCADE, null=True, blank=True, verbose_name='Estado')
	cidade = models.ForeignKey(Cidade, on_delete=models.CASCADE, null=True, blank=True, verbose_name='Cidade')
	rua = models.CharField(max_length=256, null=True, blank=True, verbose_name='Rua')
	numero = models.CharField(max_length=16, null=True, blank=True, verbose_name='Número')
	complemento = models.CharField(max_length=256, null=True, blank=True, verbose_name='Complemento')
	cep = models.CharField(max_length=16, null=True, blank=True, verbose_name='CEP')
	setor = models.ForeignKey(Setor, on_delete=models.CASCADE, null=True, blank=True, verbose_name='Setor')
	cargo = models.ForeignKey(Cargo, on_delete=models.CASCADE, null=True, blank=True, verbose_name='Cargo')
	gerente = models.ForeignKey('Funcionario', null=True, blank=True, on_delete=models.SET_NULL, verbose_name='Responsável')
	salario = models.FloatField(null=True, blank=True, verbose_name='Salário')
	data_expedicao = models.DateField(null=True, blank=True, verbose_name='Data Expedição RG')
	data_nascimento = models.DateField(null=True, blank=True, verbose_name='Data Nascimento')
	data_contratacao = models.DateField(null=True, blank=True, verbose_name='Data Contratação')
	data_demissao = models.DateField(null=True, blank=True, verbose_name='Data Rescisão')
	data_inicio_ferias = models.DateField(null=True, blank=True, verbose_name='Data Início Férias')
	observacoes = CKEditor5Field('Observacoes', null=True, blank=True, config_name='extends')
	conta_banco = models.CharField(max_length=120, null=True, blank=True, unique=True, verbose_name='Conta Bancária')
	visivel = models.BooleanField(default=True, verbose_name='Visível')
	data_cadastro = models.DateTimeField(auto_now_add=True, verbose_name='Data de Cadastro')

	def save(self, *args, **kwargs):
		if self.nome_completo:
			self.nome_completo = self.nome_completo.title()
		
		if self.nome_social:
			self.nome_social = self.nome_social.title()
		
		if self.nome_mae:
			self.nome_mae = self.nome_mae.title()
		
		if self.nome_pai:
			self.nome_pai = self.nome_pai.title()
		
		if self.rua:
			self.rua = self.rua.title()
		
		if self.complemento:
			self.complemento = self.complemento.title()
		
		if self.contato.strip().startswith('(__)') or self.contato.strip() == '':
			self.contato = None

		if self.contato_sec.strip().startswith('(__)') or self.contato_sec.strip() == '':
			self.contato_sec = None
		
		super().save(*args, **kwargs)

	def __str__(self):
		if not_none_not_empty(self.nome_social):
			return self.nome_social
		else:
			return self.nome_completo

	@property
	def get_perfil(self):
		return Perfil.objects.get(funcionario=self)
	
	@property
	def get_tag(self):
		return f"@{self.nome_completo.title().replace(' ', '')}"
	
	@property
	def get_contrato(self):
		jornadas = JornadaFuncionario.objects.filter(funcionario=self, final_vigencia=None).order_by('funcionario__id', 'dia', 'ordem')
		return jornadas.first().contrato
	
	@property
	def is_analista(self):
		return True if 'analista' in self.cargo.cargo.lower() else False
	
	@property
	def is_financeiro(self):
		return True if 'financeiro' in self.setor.setor.lower() or 'diretor' in self.cargo.cargo.lower() else False
	
	@property
	def has_docpendentes(self):
		return True if Documento.objects.filter(funcionario=self, lido=False) else False

	class Meta:
		verbose_name = 'Funcionário'
		verbose_name_plural = 'Funcionários'


class HistoricoFuncionario(models.Model):
	funcionario = models.ForeignKey(Funcionario, on_delete=models.CASCADE, verbose_name='Funcionário')
	setor = models.ForeignKey(Setor, on_delete=models.CASCADE, null=False, blank=False, verbose_name='Setor')
	cargo = models.ForeignKey(Cargo, on_delete=models.CASCADE, null=False, blank=False, verbose_name='Cargo')
	contrato = models.ForeignKey(Contrato, on_delete=models.SET_NULL, null=True, verbose_name='Contrato')
	salario = models.FloatField(null=True, blank=True, verbose_name='Salário')
	data_alteracao = models.DateField(verbose_name='Data de Alteração')
	observacao = models.TextField(null=True, blank=True, verbose_name='Observações')

	def save(self, *args, **kwargs):
		if not self.data_alteracao:
			self.data_alteracao = datetime.now().replace(tzinfo=pytz.utc)
		super().save(*args, **kwargs)

	def __str__(self):
		return f'Hitórico {self.funcionario} em {self.data_alteracao}'

	class Meta:
		verbose_name = 'Histórico Funcionário'
		verbose_name_plural = 'Histórico Funcionários'


class JornadaFuncionario(models.Model):
	funcionario = models.ForeignKey(Funcionario, on_delete=models.CASCADE, verbose_name='Funcionário')
	contrato = models.ForeignKey(Contrato, on_delete=models.SET_NULL, null=True, verbose_name='Contrato')
	tipo = models.CharField(max_length=1, choices=Jornada.Tipo.choices, editable=False, verbose_name='Tipo')
	ordem = models.IntegerField(editable=False, verbose_name='Ordem')
	dia = models.IntegerField(choices=Jornada.Semana.choices, verbose_name='Dia da Semana')
	hora = models.TimeField(verbose_name='Hora')
	inicio_vigencia = models.DateField(verbose_name='Início da Vigência')
	final_vigencia = models.DateField(null=True, blank=True, verbose_name='Final da Vigência')
	agrupador = models.IntegerField(editable=False, verbose_name='Agrupador')
	
	def save(self, *args, **kwargs):
		if not self.ordem:
			jornadas_ordem = JornadaFuncionario.objects.filter(
				funcionario=self.funcionario, contrato=self.contrato, dia=self.dia
			).order_by('ordem')

			if jornadas_ordem.exists():
				self.ordem = jornadas_ordem.last().ordem + 1
			else:
				self.ordem = 1

		if not self.tipo:
			if self.ordem % 2 == 1:
				self.tipo = Jornada.Tipo.ENTRADA
			else:
				self.tipo = Jornada.Tipo.SAIDA
		
		if not self.inicio_vigencia:
			self.inicio_vigencia = date.today()

		if not self.agrupador:
			self.agrupador = 1

		super().save(*args, **kwargs)

	def __str__(self):
		return f'{self.funcionario.nome_completo} - {self.dia} - {self.hora}'

	class Meta:
		verbose_name = 'Jornada Funcionário'
		verbose_name_plural = 'Jornada por Funcionário'


class Score(models.Model):
	funcionario = models.ForeignKey(Funcionario, on_delete=models.CASCADE, verbose_name='Funcionário')
	pontuacao = models.FloatField(default=0, verbose_name='Pontuação')
	data_cadastro = models.DateTimeField(auto_now=True, verbose_name='Data de Cadastro')

	def __str__(self):
		return f'{self.funcionario} - {self.pontuacao}'

	class Meta:
		verbose_name = 'Pontuação de Assiduidade'
		verbose_name_plural = 'Pontuações de Assiduidade'


class TipoDocumento(models.Model):
	class Visoes(models.TextChoices):
		GERAL = 'GERAL', 'Visibilidade Geral'
		FINA = 'FINA', 'Apenas Financeiro'
		ADMIN = 'ADMIN', 'Apenas acesso Admin'
		OCULTO = 'OCULTO', 'Oculto'

	tipo = models.CharField(max_length=120, null=False, blank=False, verbose_name='Tipo de Documento')
	slug = models.SlugField(default='', editable=False, null=True, blank=True, max_length=120)
	codigo = models.CharField(max_length=12, unique=True, null=True, blank=True, verbose_name='Código')
	data_cadastro = models.DateTimeField(auto_now_add=True, verbose_name='Data de Cadastro')
	visibilidade = models.CharField(choices=Visoes.choices, default=Visoes.GERAL, max_length=6)

	def save(self, *args, **kwargs):
		self.slug = slugify(self.tipo, allow_unicode=False)
		super().save(*args, **kwargs)

	def __str__(self):
		return f'{self.tipo} - {self.codigo}'

	class Meta:
		verbose_name = 'Tipo Documento'
		verbose_name_plural = 'Tipos Documento'


class Documento(models.Model):
	funcionario = models.ForeignKey(Funcionario, on_delete=models.CASCADE, null=True, blank=True, verbose_name='Funcionário')
	tipo = models.ForeignKey(TipoDocumento, on_delete=models.SET_NULL, null=True, blank=True, verbose_name='Tipo')
	caminho = models.CharField(max_length=256, verbose_name='Caminho do Documento')
	data_documento = models.DateField(null=True, blank=True, verbose_name='Data do Documento')
	lido = models.BooleanField(default=False, verbose_name='Visualizado')
	data_cadastro = models.DateTimeField(auto_now_add=True, verbose_name='Data de Cadastro')

	def __str__(self):
		return f'Documento: {self.caminho}'

	@property
	def get_short_name(self):
		return self.caminho.split('\\')[-1]
	
	class Meta:
		verbose_name = 'Documento'
		verbose_name_plural = 'Documentos'


class Perfil(models.Model):
	class StatusChat(models.IntegerChoices):
		DISPONIVEL = 1, 'Disponível'
		AUSENTE = 2, 'Ausente'
		OCUPADO = 3, 'Ocupado'
	
	def upload(instance, filename):
		caminho = 'fotos/{matricula}/{filename}'.format(matricula=(instance.funcionario.matricula), filename=re.sub('[^A-Za-z0-9.]+', '', filename))
		return caminho

	funcionario = models.ForeignKey(Funcionario, on_delete=models.CASCADE, verbose_name='Funcionário')
	foto = models.ImageField(upload_to=upload, null=True, blank=True, verbose_name='Foto')
	bio = models.TextField(verbose_name='Biografia', null=True, blank=True)
	tema = models.CharField(max_length=10, editable=False, default='light', verbose_name='Tema')
	status = models.IntegerField(choices=StatusChat.choices, default=StatusChat.DISPONIVEL)
	data_edicao = models.DateTimeField(auto_now=True, verbose_name='Data de Edição')

	def __str__(self):
		return f'Perfil do funcionário {self.funcionario}'

	class Meta:
		verbose_name = 'Perfil'
		verbose_name_plural = 'Perfis'


class Feedback(models.Model):
	class Modelos(models.TextChoices):
		PCC = 'PCC', 'Parar / Continuar / Começar'
		SCI = 'SCI', 'Situação, Comportamento ou Impacto'
		CNV = 'CNV', 'Comunicação Não Violenta'
		GRL = 'GRL', 'Geral'

	class Pontuacao(models.IntegerChoices):
		MINIMO = 1, 'Cumpriu Minimamente'
		PARCIAL = 2, 'Cumpriu Parcialmente'
		MODERADO = 3, 'Cumriu Moderadamente'
		SUFICIENTE = 4, 'Cumpriu Suficientemente'
		TOTAL = 5, 'Cumpriu Totalmente'

	remetente = models.ForeignKey(Funcionario, on_delete=models.CASCADE, related_name='feedback_remetente', verbose_name='Remetente')
	destinatario = models.ForeignKey(Funcionario, on_delete=models.CASCADE, null=True, blank=True, related_name='feedback_destinatario', verbose_name='Destinatário')
	modelo = models.CharField(choices=Modelos.choices, max_length=3)
	mensagem = CKEditor5Field('Mensagem', config_name='extends')
	comprometimento = models.IntegerField(choices=Pontuacao.choices, verbose_name='Comprometimento')
	conhecimento = models.IntegerField(choices=Pontuacao.choices, verbose_name='Conhecimento')
	produtividade = models.IntegerField(choices=Pontuacao.choices, verbose_name='Produtividade')
	comportamento = models.IntegerField(choices=Pontuacao.choices, verbose_name='Comportamento')
	anonimo = models.BooleanField(default=False, verbose_name='Anônimo')
	data_cadastro = models.DateTimeField(auto_now_add=True, verbose_name='Data de Cadastro')

	def __str__(self):
		return f'Feedback de {self.remetente.nome_completo} para {self.destinatario.nome_completo}'

	class Meta:
		verbose_name = 'Feedback'
		verbose_name_plural = 'Feedbacks'


class SolicitacaoFeedback(models.Model):
	remetente = models.ForeignKey(Funcionario, on_delete=models.CASCADE, related_name='solicitacao_feedback_remetente', verbose_name='Remetente')
	destinatario = models.ForeignKey(Funcionario, on_delete=models.CASCADE, related_name='solicitacao_feedback_destinatario', verbose_name='Destinatário')
	solicitacao = models.TextField(verbose_name='Solicitação')
	data_cadastro = models.DateTimeField(auto_now_add=True, verbose_name='Data de Cadastro')

	def __str__(self):
		return f'Solicitação de Feedback de {self.remetente.nome_completo} para {self.destinatario.nome_completo}'

	class Meta:
		verbose_name = 'Solicitação de Feedback'
		verbose_name_plural = 'Solicitações de Feedback'


class RespostaFeedback(models.Model):
	feedback = models.ForeignKey(Feedback, on_delete=models.CASCADE, verbose_name='Feedback')
	resposta = models.TextField(verbose_name='Resposta')
	util = models.BooleanField(default=True, verbose_name='Útil')
	data_cadastro = models.DateTimeField(auto_now_add=True, verbose_name='Data de Cadastro')

	def __str__(self):
		return f'Resposta de Feedback de {self.feedback.remetente.nome_completo} para {self.feedback.destinatario.nome_completo}'

	class Meta:
		verbose_name = 'Resposta de Feedback'
		verbose_name_plural = 'Respostas de Feedback'


class Estabilidade(models.Model):
	funcionario = models.ForeignKey(Funcionario, on_delete=models.CASCADE, verbose_name='Funcionário')
	inicio = models.DateField(verbose_name='Início Período')
	final = models.DateField(verbose_name='Final Período')
	observacao = models.TextField(null=True, blank=True, verbose_name='Observações')
	data_cadastro = models.DateTimeField(auto_now_add=True, verbose_name='Data de Cadastro')

	def __str__(self):
		return f'Estabilidade de {self.funcionario} do período de {self.inicio} até {self.final}'
	
	class Meta:
		verbose_name = 'Estabilidade Funcionário'
		verbose_name_plural = 'Estabilidade Funcionários'
