from django.contrib import admin

from pesquisa.models import Pesquisa, Pergunta, Resposta


admin.site.register(Pesquisa)
admin.site.register(Pergunta)
admin.site.register(Resposta)
