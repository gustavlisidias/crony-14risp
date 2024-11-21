from django.contrib import admin

from avaliacoes.models import Avaliacao, Nivel, Pergunta, PerguntaAvaliacao, Resposta


admin.site.register(Avaliacao)
admin.site.register(Nivel)
admin.site.register(Pergunta)
admin.site.register(PerguntaAvaliacao)
admin.site.register(Resposta)
