from django.contrib import admin

from pesquisa.models import Pesquisa, Pergunta, TextoPerguntas, Resposta


admin.site.register(Pesquisa)
admin.site.register(Pergunta)
admin.site.register(TextoPerguntas)
admin.site.register(Resposta)
