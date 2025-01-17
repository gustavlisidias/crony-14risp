from django.contrib import admin

from chat.models import Sala, Mensagem, Arquivo


admin.site.register(Sala)
admin.site.register(Mensagem)
admin.site.register(Arquivo)
