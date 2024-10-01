from django.contrib import admin

from agenda.models import Atividade, Avaliacao, SolicitacaoFerias, DocumentosFerias, Ferias, TipoAtividade


admin.site.register(SolicitacaoFerias)
admin.site.register(DocumentosFerias)
admin.site.register(Ferias)
admin.site.register(TipoAtividade)
admin.site.register(Atividade)
admin.site.register(Avaliacao)
