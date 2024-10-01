from django.urls import path

from avaliacao.views import AvaliacaoView, AvaliacaoDetalhesView


urlpatterns = [
	path('avaliacao', AvaliacaoView, name='avaliacao'),
	path('avaliacao/detalhes/<int:avaid>', AvaliacaoDetalhesView, name='detalhes-avaliacao'),
]
