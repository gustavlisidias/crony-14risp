from django import forms
from django.contrib import admin
from django.utils.html import format_html

from import_export.admin import ImportExportModelAdmin

from agenda.models import Atividade, Avaliacao, SolicitacaoFerias, DocumentosFerias, Ferias, TipoAtividade
from funcionarios.models import Funcionario


class FuncionarioForm(forms.ModelForm):
	'''
	Formulário base reutilizável para registros que possuem funcionários.
	Filtra funcionários ativos.
	'''
	def __init__(self, *args, **kwargs):
		super().__init__(*args, **kwargs)

		query = Funcionario.objects.all().order_by('nome_completo')
		
		if 'funcionarios' in self.fields:
			self.fields['funcionarios'].queryset = query
		if 'funcionario' in self.fields:
			self.fields['funcionario'].queryset = query
		if 'avaliado' in self.fields:
			self.fields['avaliado'].queryset = query
		if 'avaliadores' in self.fields:
			self.fields['avaliadores'].queryset = query
		if 'celebrante' in self.fields:
			self.fields['celebrante'].queryset = query
		if 'remetente' in self.fields:
			self.fields['remetente'].queryset = query
		if 'destinatario' in self.fields:
			self.fields['destinatario'].queryset = query
		if 'responsavel' in self.fields:
			self.fields['responsavel'].queryset = query


class DocumentoInline(admin.TabularInline):
	model = DocumentosFerias
	extra = 0
	fields = ('documento', 'caminho', 'data_cadastro')
	readonly_fields = ('documento', 'caminho', 'data_cadastro')
	can_delete = True


@admin.register(TipoAtividade)
class TipoAtividadeAdmin(admin.ModelAdmin):
	list_display = ('tipo', 'cor_visual', 'avaliativo', 'data_cadastro') # colunas da tabela
	search_fields = ('tipo',) # campos de pesquisa aberta
	ordering = ('tipo',) # ordenção da tabela

	def cor_visual(self, obj):
		return format_html(
			'<div style="width: 30px; height: 20px; background-color: {}; border: 1px solid #eee; border-radius: 5px" title="{}"></div>',
			obj.cor, obj.cor
		)
	cor_visual.short_description = 'Cor'


@admin.register(Atividade)
class AtividadeAdmin(ImportExportModelAdmin):
	form = FuncionarioForm
	list_display = ('titulo', 'tipo', 'inicio', 'final', 'autor') # colunas da tabela
	search_fields = ('funcionarios__nome_completo', 'titulo') # campos de pesquisa aberta
	ordering = ('-data_cadastro', 'funcionarios__nome_completo') # ordenção da tabela


@admin.register(Avaliacao)
class AvaliacaoAdmin(admin.ModelAdmin):
	form = FuncionarioForm
	list_display = ('atividade', 'potencial', 'desempenho', 'avaliador') # colunas da tabela
	search_fields = ('atividade__funcionarios__nome_completo', 'avaliador__nome_completo') # campos de pesquisa aberta
	ordering = ('-data_cadastro', 'atividade__funcionarios__nome_completo') # ordenção da tabela


@admin.register(SolicitacaoFerias)
class SolicitacaoFeriasAdmin(admin.ModelAdmin):
	form = FuncionarioForm
	list_display = ('observacao', 'funcionario', 'inicio_periodo', 'final_periodo', 'inicio_ferias', 'final_ferias', 'abono', 'decimo', 'status') # colunas da tabela
	search_fields = ('observacao', 'funcionario__nome_completo') # campos de pesquisa aberta
	ordering = ('-inicio_ferias', 'funcionario__nome_completo') # ordenção da tabela
	inlines = [DocumentoInline, ]


@admin.register(Ferias)
class FeriasAdmin(admin.ModelAdmin):
	form = FuncionarioForm
	list_display = ('funcionario', 'ano_referencia', 'inicio_periodo', 'final_periodo', 'saldo') # colunas da tabela
	search_fields = ('funcionario__nome_completo', 'ano_referencia') # campos de pesquisa aberta
	ordering = ('funcionario__nome_completo', 'ano_referencia') # ordenção da tabela
