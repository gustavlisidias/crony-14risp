from django.urls import path

from web.ajax import (
	ProcurarCidadesView,
	AlterarTemaView,
	EditarOuvidoriaView,
	FuncionariosTagsView,
	CurtirPostView,
	VisualizarReacoesView,
	VisualizarComentariosView
)
from web.views import (
	InicioView, 
	RankingView, 
	AdicionarMoedaView,
	AdicionarPostView,
	ComentarPostView,
	EditarComentarioView,
	EditarPostView,
	ExcluirComentarioView,
	ExcluirPostView,
	AdicionarCelebracaoView,
	OuvidoriaView,
	AdicionarOuvidoriaView
)


urlpatterns = [
	path('', InicioView, name='inicio'),
	path('alterar/tema', AlterarTemaView, name='alterar-tema'),
	path('ranking', RankingView, name='ranking'),
	path('procurar/cidade/<int:estado>', ProcurarCidadesView, name='procurar-cidades'),
	path('moedas/adicionar/<int:fecid>', AdicionarMoedaView, name='adicionar-moedas'),
	path('consultar/funcionarios/tags', FuncionariosTagsView, name='funcionarios-tags'),

	path('posts/adicionar/celebracao', AdicionarCelebracaoView, name='adicionar-celebracao'),
	path('posts/adicionar/postagem', AdicionarPostView, name='adicionar-post'),
	path('posts/curtir/<int:post>/tipo/<str:modelo>', CurtirPostView, name='curtir-post'),
	path('posts/comentar/<int:post>/tipo/<str:modelo>', ComentarPostView, name='comentar-post'),
	path('posts/reacoes/<int:post>/tipo/<str:modelo>', VisualizarReacoesView, name='reacoes-post'),
	path('posts/comentarios/<int:post>/tipo/<str:modelo>', VisualizarComentariosView, name='comentarios-post'),
	path('posts/editar/<int:post>', EditarPostView, name='editar-post'),
	path('posts/excluir/<int:post>', ExcluirPostView, name='excluir-post'),
	path('posts/editar/comentario/<int:comment>', EditarComentarioView, name='editar-comentario'),
	path('posts/excluir/comentario/<int:comment>', ExcluirComentarioView, name='excluir-comentario'),

	path('ouvidoria', OuvidoriaView, name='ouvidoria'),
	path('ouvidoria/adicionar/manifestacao', AdicionarOuvidoriaView, name='adicionar-ouvidoria'),
	path('ouvidoria/editar/manifestacao/<int:ticket>', EditarOuvidoriaView, name='editar-ouvidoria'),
]
