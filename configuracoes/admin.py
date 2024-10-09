from django.contrib import admin
from django.contrib.auth.models import Group
from django.contrib.admin.models import LogEntry

from configuracoes.auth import UserAdmin
from configuracoes.models import Contrato, Jornada, Usuario, Variavel


admin.site.unregister(Group)

admin.site.register(Usuario, UserAdmin)
admin.site.register(Contrato)
admin.site.register(Jornada)
admin.site.register(Variavel)


@admin.register(LogEntry)
class LogAdmin(admin.ModelAdmin):
	list_display = ('user', 'content_type', 'action_flag', 'object_repr', 'action_time') # colunas da tabela
	search_fields = ('user', 'content_type', 'action_flag', 'object_repr') # campos de pesquisa aberta
	ordering = ('-action_time', 'user') # ordenção da tabela
	list_filter = ('action_flag', ) # filtros
