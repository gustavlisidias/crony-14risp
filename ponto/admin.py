from django.contrib import admin
from ponto.models import Ponto, SolicitacaoPonto, SolicitacaoAbono, Saldos, Feriados

# Register your models here.
admin.site.register(Feriados)


@admin.register(Ponto)
class PontoAdmin(admin.ModelAdmin):
	list_display = ('funcionario', 'data', 'hora', 'motivo', 'alterado', 'encerrado', 'data_fechamento') # colunas da tabela
	search_fields = ('funcionario__nome_completo', 'data', 'hora', 'motivo') # campos de pesquisa aberta
	ordering = ('-data', 'funcionario', 'hora') # ordenção da tabela
	list_filter = ('alterado', 'encerrado', 'data') # filtros
	readonly_fields = ('autor_modificacao', 'data_modificacao')


@admin.register(Saldos)
class SaldosAdmin(admin.ModelAdmin):
	list_display = ('funcionario', 'data', 'saldo', 'data_cadastro') # colunas da tabela
	search_fields = ('funcionario__nome_completo', 'data') # campos de pesquisa aberta
	ordering = ('-data', 'funcionario__nome_completo') # ordenção da tabela
	list_filter = ('data', 'data_cadastro') # filtros


@admin.register(SolicitacaoPonto)
class SolicitacaoPontoAdmin(admin.ModelAdmin):
	list_display = ('funcionario', 'data', 'hora', 'data_cadastro', 'status') # colunas da tabela
	search_fields = ('funcionario__nome_completo', 'aprovador__nome_completo', 'motivo', 'data') # campos de pesquisa aberta
	ordering = ('-data', 'funcionario__nome_completo') # ordenção da tabela
	list_filter = ('data', 'status') # filtros


@admin.register(SolicitacaoAbono)
class SolicitacaoAbonoAdmin(admin.ModelAdmin):
	list_display = ('funcionario', 'inicio', 'data_cadastro', 'status') # colunas da tabela
	search_fields = ('funcionario__nome_completo', 'aprovador__nome_completo', 'motivo', 'inicio') # campos de pesquisa aberta
	ordering = ('-inicio', 'funcionario__nome_completo') # ordenção da tabela
	list_filter = ('inicio', 'status') # filtros