from django.urls import path

from avaliacoes.views import AvaliacaoView, AvaliacaoDetalhesView, DuplicarAvaliacaoView


urlpatterns = [
	path('avaliacao', AvaliacaoView, name='avaliacao'),
	path('avaliacao/detalhes/<int:avaid>', AvaliacaoDetalhesView, name='detalhes-avaliacao'),
	path('avaliacao/duplicar/<int:avaid>', DuplicarAvaliacaoView, name='duplicar-avaliacao'),
]
