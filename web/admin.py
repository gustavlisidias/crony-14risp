from django.contrib import admin
from web.models import Postagem, Curtida, Comentario, Humor, Ouvidoria, MensagemOuvidoria, Celebracao, Sugestao, Moeda

admin.site.register(Postagem)
admin.site.register(Curtida)
admin.site.register(Comentario)
admin.site.register(Humor)
admin.site.register(Celebracao)
admin.site.register(Ouvidoria)
admin.site.register(MensagemOuvidoria)
admin.site.register(Sugestao)
admin.site.register(Moeda)
