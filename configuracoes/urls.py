from django.urls import path

from configuracoes.views import (
	ConfiguracoesView,
	AdicionarJornadaView,
)


urlpatterns = [
	path('configuracoes', ConfiguracoesView, name='configuracoes'),
	path('configuracoes/adicionar/jornada', AdicionarJornadaView, name='adicionar-jornada'),
]
