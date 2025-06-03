from django.contrib import admin
from django.contrib.auth.models import Group
from django.contrib.admin.models import LogEntry

from agenda.admin import FuncionarioForm
from configuracoes.auth import UserAdmin
from configuracoes.models import Contrato, Jornada, Usuario, Variavel


admin.site.unregister(Group)
admin.site.register(Usuario, UserAdmin)


@admin.register(Contrato)
class ContratoAdmin(admin.ModelAdmin):
	list_display = ('titulo', 'descricao', 'tipo', 'data_cadastro') # colunas da tabela
	search_fields = ('titulo', 'descricao', 'tipo') # campos de pesquisa aberta
	ordering = ('titulo',) # ordenção da tabela


@admin.register(Jornada)
class JornadaAdmin(admin.ModelAdmin):
	list_display = ('contrato', 'tipo', 'ordem', 'dia', 'hora') # colunas da tabela
	search_fields = ('contrato__titulo', 'tipo', 'dia') # campos de pesquisa aberta
	ordering = ('contrato', 'dia', 'ordem') # ordenção da tabela


@admin.register(Variavel)
class VariavelAdmin(admin.ModelAdmin):
	form = FuncionarioForm
	list_display = ('chave', 'valor') # colunas da tabela
	search_fields = ('chave', 'valor') # campos de pesquisa aberta
	ordering = ('chave',) # ordenção da tabela


@admin.register(LogEntry)
class LogAdmin(admin.ModelAdmin):
	list_display = ('user', 'content_type', 'action_flag', 'object_repr', 'action_time') # colunas da tabela
	search_fields = ('user__username', 'content_type__model', 'content_type__app_label') # campos de pesquisa aberta
	ordering = ('-action_time', 'user__username') # ordenção da tabela
	list_filter = ('action_flag', 'action_time') # filtros
