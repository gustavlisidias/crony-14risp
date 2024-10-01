from django.urls import path

from pesquisa.ajax import VisualizarPesquisaView, ExcluirPesquisaView
from pesquisa.views import PesquisaView, EditarPesquisaView, ResponderPesquisaView, VisualizarRespostasView


urlpatterns = [
	path('pesquisas', PesquisaView, name='pesquisa'),
	path('pesquisas/visualizar/<int:pesqid>', VisualizarPesquisaView, name='visualizar-pesquisa'),
	path('pesquisas/respostas/<int:pesqid>', VisualizarRespostasView, name='visualizar-respostas'),
	path('pesquisas/editar/<int:pesqid>', EditarPesquisaView, name='editar-pesquisa'),
	path('pesquisas/responder/int:<pesqid>', ResponderPesquisaView, name='responder-pesquisa'),
	path('pesquisas/excluir/<int:pesqid>', ExcluirPesquisaView, name='excluir-pesquisa'),
]
