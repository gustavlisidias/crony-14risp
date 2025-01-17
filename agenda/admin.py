from django.contrib import admin

from agenda.models import Atividade, Avaliacao, SolicitacaoFerias, DocumentosFerias, Ferias, TipoAtividade


admin.site.register(SolicitacaoFerias)
admin.site.register(DocumentosFerias)
admin.site.register(TipoAtividade)
admin.site.register(Atividade)
admin.site.register(Avaliacao)


@admin.register(Ferias)
class FeriasAdmin(admin.ModelAdmin):
	list_display = ('funcionario', 'ano_referencia', 'inicio_periodo', 'final_periodo', 'saldo') # colunas da tabela
	search_fields = ('funcionario__nome_completo', 'ano_referencia') # campos de pesquisa aberta
	ordering = ('funcionario__nome_completo', 'ano_referencia') # ordenção da tabela
