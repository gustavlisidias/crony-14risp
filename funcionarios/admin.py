from django.contrib import admin

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
	HistoricoFuncionario
)


admin.site.register(Setor)
admin.site.register(Cargo)
admin.site.register(JornadaFuncionario)
admin.site.register(TipoDocumento)
admin.site.register(Score)
admin.site.register(Feedback)
admin.site.register(SolicitacaoFeedback)
admin.site.register(RespostaFeedback)
admin.site.register(HistoricoFuncionario)


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
		'gerente'
	)


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
