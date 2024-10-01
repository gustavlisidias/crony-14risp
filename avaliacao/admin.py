from django.contrib import admin

from avaliacao.models import Avaliacao, Criterio, Pergunta, PesoCriterio, PesoAvaliador, Resposta


admin.site.register(Avaliacao)
admin.site.register(Criterio)
admin.site.register(Pergunta)
admin.site.register(PesoCriterio)
admin.site.register(PesoAvaliador)
admin.site.register(Resposta)
