from django.contrib import admin
from ponto.models import Ponto, SolicitacaoPonto, SolicitacaoAbono, Saldos, Feriados

# Register your models here.
admin.site.register(Ponto)
admin.site.register(SolicitacaoPonto)
admin.site.register(SolicitacaoAbono)
admin.site.register(Saldos)
admin.site.register(Feriados)
