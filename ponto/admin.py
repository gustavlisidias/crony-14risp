from django.contrib import admin
from ponto.models import Ponto, SolicitacaoPonto, SolicitacaoAbono, Saldos, Feriados

# Register your models here.
admin.site.register(SolicitacaoPonto)
admin.site.register(SolicitacaoAbono)
admin.site.register(Saldos)
admin.site.register(Feriados)


@admin.register(Ponto)
class PontoAdmin(admin.ModelAdmin):
	list_display = ('funcionario', 'data', 'hora', 'motivo', 'alterado', 'encerrado', 'data_fechamento') # colunas da tabela
	search_fields = ('funcionario__nome_completo', 'data', 'hora', 'motivo') # campos de pesquisa aberta
	ordering = ('-data', 'hora', 'funcionario') # ordenção da tabela
	list_filter = ('alterado', 'encerrado', 'data') # filtros
