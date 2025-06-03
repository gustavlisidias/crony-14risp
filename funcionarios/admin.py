from django.contrib import admin

from agenda.admin import FuncionarioForm
from funcionarios.models import (
	Cargo,
	Documento,
	Funcionario,
	JornadaFuncionario,
	Perfil,
	Score,
	Setor,
	TipoDocumento,
	Feedback,
	SolicitacaoFeedback,
	RespostaFeedback,
	HistoricoFuncionario,
	Estabilidade
)
from ponto.renderers import RenderToPDF


@admin.register(Setor)
class SetorAdmin(admin.ModelAdmin):
	form = FuncionarioForm
	list_display = ('setor', 'data_cadastro') # colunas da tabela
	search_fields = ('setor',) # campos de pesquisa aberta
	ordering = ('setor',) # ordenção da tabela


@admin.register(Cargo)
class CargoAdmin(admin.ModelAdmin):
	list_display = ('cargo', 'data_cadastro') # colunas da tabela
	search_fields = ('cargo',) # campos de pesquisa aberta
	ordering = ('cargo',) # ordenção da tabela


@admin.register(Estabilidade)
class EstabilidadeAdmin(admin.ModelAdmin):
	form = FuncionarioForm
	list_display = ('funcionario', 'observacao', 'inicio', 'final', 'data_cadastro') # colunas da tabela
	search_fields = ('funcionario__nome_completo',) # campos de pesquisa aberta
	ordering = ('-data_cadastro',) # ordenção da tabela


@admin.register(TipoDocumento)
class TipoDocumentoAdmin(admin.ModelAdmin):
	list_display = ('tipo', 'codigo', 'data_cadastro') # colunas da tabela
	search_fields = ('tipo', 'codigo') # campos de pesquisa aberta
	ordering = ('codigo',) # ordenção da tabela


@admin.register(JornadaFuncionario)
class JornadaFuncionarioAdmin(admin.ModelAdmin):
	form = FuncionarioForm
	list_display = ('funcionario', 'contrato', 'dia', 'ordem', 'hora', 'agrupador', 'inicio_vigencia', 'final_vigencia') # colunas da tabela
	search_fields = ('funcionario__nome_completo', 'contrato__titulo') # campos de pesquisa aberta
	ordering = ('funcionario__nome_completo', 'agrupador', 'dia', 'ordem') # ordenção da tabela


@admin.register(HistoricoFuncionario)
class HistoricoFuncionarioAdmin(admin.ModelAdmin):
	form = FuncionarioForm
	list_display = ('funcionario', 'setor', 'cargo', 'contrato', 'data_alteracao') # colunas da tabela
	search_fields = ('funcionario__nome_completo', 'setor__setor', 'cargo__cargo', 'contrato__titulo') # campos de pesquisa aberta
	ordering = ('funcionario',) # ordenção da tabela


@admin.register(Feedback)
class FeedbackAdmin(admin.ModelAdmin):
	form = FuncionarioForm
	list_display = ('remetente', 'destinatario', 'modelo', 'comprometimento', 'conhecimento', 'produtividade', 'comportamento', 'anonimo', 'data_cadastro') # colunas da tabela
	search_fields = ('remetente__nome_completo', 'destinatario__nome_completo', 'modelo') # campos de pesquisa aberta
	ordering = ('-data_cadastro',) # ordenção da tabela


@admin.register(SolicitacaoFeedback)
class SolicitacaoFeedbackAdmin(admin.ModelAdmin):
	form = FuncionarioForm
	list_display = ('remetente', 'destinatario', 'solicitacao', 'data_cadastro') # colunas da tabela
	search_fields = ('remetente__nome_completo', 'destinatario__nome_completo') # campos de pesquisa aberta
	ordering = ('-data_cadastro',) # ordenção da tabela


@admin.register(RespostaFeedback)
class RespostaFeedbackAdmin(admin.ModelAdmin):
	form = FuncionarioForm
	list_display = ('feedback', 'util', 'data_cadastro') # colunas da tabela
	search_fields = ('feedback__remetente', 'feedback__destinatario', 'resposta') # campos de pesquisa aberta
	ordering = ('-data_cadastro',) # ordenção da tabela


@admin.register(Funcionario)
class FuncionarioAdmin(admin.ModelAdmin):
	list_display = ('matricula', 'nome_completo', 'email', 'contato', 'cpf', 'rg', 'data_nascimento') # colunas da tabela
	search_fields = ('matricula', 'nome_completo', 'email', 'contato', 'cpf', 'rg') # campos de pesquisa aberta
	ordering = ('-data_demissao', 'nome_completo') # ordenção da tabela
	list_filter = (
		# filtros
		'sexo',
		'estado_civil',
		'estado',
		'cidade',
		'cargo',
		'setor',
		'gerente',
		'data_demissao'
	)
	actions = ['relatorio_observacoes']

	@admin.action(description='Relatório de Observações')
	def relatorio_observacoes(self, request, queryset):
		context = {'autor': request.user, 'dados':  list()}
		filename = 'relatorio_observacoes.pdf'

		for funcionario in queryset.all():
			context['dados'].append({
				'matricula': funcionario.matricula,
				'nome_completo': funcionario.nome_completo,
				'observacoes': funcionario.observacoes
			})
		
		pdf = RenderToPDF(request, 'relatorios/observacoes.html', context, filename).weasyprint()
		return pdf


@admin.register(Perfil)
class PerfilAdmin(admin.ModelAdmin):
	list_display = ('funcionario', 'foto', 'data_edicao') # colunas da tabela
	search_fields = ('funcionario__nome_completo',) # campos de pesquisa aberta
	ordering = ('funcionario__nome_completo',) # ordenção da tabela


@admin.register(Documento)
class DocumentoAdmin(admin.ModelAdmin):
	list_display = ('caminho', 'tipo', 'funcionario', 'data_documento') # colunas da tabela
	search_fields = ('caminho', 'funcionario__nome_completo', 'data_documento') # campos de pesquisa aberta
	ordering = ('-data_documento', 'funcionario__nome_completo', 'tipo') # ordenção da tabela
	list_filter = ('tipo', 'data_documento') # filtros


@admin.register(Score)
class ScoreAdmin(admin.ModelAdmin):
	list_display = ('funcionario', 'pontuacao', 'data_cadastro') # colunas da tabela
	search_fields = ('funcionario__nome_completo',) # campos de pesquisa aberta
	ordering = ('-data_cadastro__date', 'funcionario__nome_completo') # ordenção da tabela
