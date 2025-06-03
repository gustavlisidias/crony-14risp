from django.contrib import admin

from agenda.admin import FuncionarioForm
from funcionarios.models import Funcionario
from ponto.models import Ponto, SolicitacaoPonto, SolicitacaoAbono, Saldos, Feriados, Fechamento


# Register your models here.
@admin.register(Feriados)
class FeriadosAdmin(admin.ModelAdmin):
	list_display = ('titulo', 'data', 'regiao', 'estado', 'cidade', 'data_cadastro') # colunas da tabela
	search_fields = ('titulo',) # campos de pesquisa aberta
	ordering = ('-data',) # ordenção da tabela


@admin.register(Fechamento)
class FechamentoAdmin(admin.ModelAdmin):
	form = FuncionarioForm
	list_display = ('funcionario', 'pontuacao', 'moedas', 'referencia', 'data_cadastro') # colunas da tabela
	search_fields = ('funcionario__nome_completo', 'referencia') # campos de pesquisa aberta
	ordering = ('-referencia', 'funcionario__nome_completo') # ordenção da tabela


@admin.register(Ponto)
class PontoAdmin(admin.ModelAdmin):
	form = FuncionarioForm
	list_display = ('funcionario', 'data', 'hora', 'motivo', 'alterado', 'encerrado') # colunas da tabela
	search_fields = ('funcionario__nome_completo', 'data', 'hora', 'motivo') # campos de pesquisa aberta
	ordering = ('-data', 'funcionario', 'hora') # ordenção da tabela
	list_filter = ('alterado', 'encerrado', 'data') # filtros
	readonly_fields = ('autor_modificacao', 'data_modificacao')

	def save_model(self, request, obj, form, change):
		obj.autor_modificacao = Funcionario.objects.get(usuario=request.user)
		obj.save()


@admin.register(Saldos)
class SaldosAdmin(admin.ModelAdmin):
	form = FuncionarioForm
	list_display = ('funcionario', 'data', 'saldo', 'data_cadastro') # colunas da tabela
	search_fields = ('funcionario__nome_completo', 'data') # campos de pesquisa aberta
	ordering = ('-data', 'funcionario__nome_completo') # ordenção da tabela
	list_filter = ('data', 'data_cadastro') # filtros


@admin.register(SolicitacaoPonto)
class SolicitacaoPontoAdmin(admin.ModelAdmin):
	form = FuncionarioForm
	list_display = ('funcionario', 'data', 'hora', 'data_cadastro', 'status') # colunas da tabela
	search_fields = ('funcionario__nome_completo', 'aprovador__nome_completo', 'motivo', 'data') # campos de pesquisa aberta
	ordering = ('-data', 'funcionario__nome_completo') # ordenção da tabela
	list_filter = ('data', 'status') # filtros


@admin.register(SolicitacaoAbono)
class SolicitacaoAbonoAdmin(admin.ModelAdmin):
	form = FuncionarioForm
	list_display = ('funcionario', 'inicio', 'data_cadastro', 'status') # colunas da tabela
	search_fields = ('funcionario__nome_completo', 'aprovador__nome_completo', 'motivo', 'inicio') # campos de pesquisa aberta
	ordering = ('-inicio', 'funcionario__nome_completo') # ordenção da tabela
	list_filter = ('inicio', 'status') # filtros
