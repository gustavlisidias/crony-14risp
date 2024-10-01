from django.contrib import admin
from django.contrib.auth.models import Group
from django.contrib.admin.models import LogEntry

from configuracoes.auth import UserAdmin
from configuracoes.models import Contrato, Jornada, Usuario, Variavel


admin.site.unregister(Group)
admin.site.register(LogEntry)

admin.site.register(Usuario, UserAdmin)
admin.site.register(Contrato)
admin.site.register(Jornada)
admin.site.register(Variavel)
