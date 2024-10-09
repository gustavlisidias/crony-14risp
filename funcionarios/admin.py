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
	Time,
	Feedback,
	SolicitacaoFeedback,
	RespostaFeedback,
	HistoricoFuncionario
)


admin.site.register(Setor)
admin.site.register(Cargo)
admin.site.register(JornadaFuncionario)
admin.site.register(TipoDocumento)
admin.site.register(Perfil)
admin.site.register(Score)
admin.site.register(Time)
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


@admin.register(Documento)
class DocumentoAdmin(admin.ModelAdmin):
	list_display = ('caminho', 'tipo', 'funcionario', 'data_documento') # colunas da tabela
	search_fields = ('caminho', 'funcionario', 'data_documento') # campos de pesquisa aberta
	ordering = ('-data_documento', 'funcionario', 'tipo') # ordenção da tabela
	list_filter = ('tipo', 'data_documento') # filtros
