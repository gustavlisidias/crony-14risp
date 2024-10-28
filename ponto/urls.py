from django.urls import path

from ponto.ajax import (
	AprovarSolicitacaoView,
	ConsultarPontoView,
	ConsultarSolicitacaoView,
	EditarPontoView,
	ReprovarSolicitacaoView,
	RegistrarPontoView,
	RelatoriosPontoView,
	AprovarSolicitacoesView,
	ReprovarSolicitacoesView
)
from ponto.views import (
	RegistrosPontoView,
	RegistrosPontoFuncinarioView,
	SolicitarAbonoView,
	AdicionarFeriadoView,
	AdicionarSaldoView,
	ExcluirFechamentoView,
	RegistrarPontoExternoView
)


urlpatterns = [
	path('ponto', RegistrosPontoView, name='pontos'),
	path('ponto/relatorio', RelatoriosPontoView, name='relatorio-ponto'),
	path('ponto/registrar', RegistrarPontoView, name='registrar-ponto'),
	path('ponto/registrar/externo', RegistrarPontoExternoView, name='registrar-externo'),
	path('ponto/consultar/data/<str:data>/funcionario/<int:func>', ConsultarPontoView, name='consultar-ponto'),
	path('ponto/editar/data/<str:data>/funcionario/<int:func>', EditarPontoView, name='editar-ponto'),
	path('ponto/solicitar/abono', SolicitarAbonoView, name='solicitar-abono'),
	path('ponto/excluir/solicitacao/<int:solic>/<str:categoria>', ReprovarSolicitacaoView, name='excluir-solicitacao'),
	path('ponto/aprovar/solicitacao/<int:solic>/<str:categoria>', AprovarSolicitacaoView, name='aprovar-solicitacao'),
	path('ponto/consultar/solicitacao/<int:solic>/<str:categoria>', ConsultarSolicitacaoView, name='consultar-solicitacao'),
	path('ponto/aprovar/solicitacoes', AprovarSolicitacoesView, name='aprovar-solicitacoes'),
	path('ponto/reprovar/solicitacoes', ReprovarSolicitacoesView, name='reprovar-solicitacoes'),
	path('ponto/feriado/adicionar', AdicionarFeriadoView, name='adicionar-feriado'),
	path('ponto/saldo/adicionar', AdicionarSaldoView, name='adicionar-saldo'),
	path('ponto/funcionario/<int:func>/detalhes', RegistrosPontoFuncinarioView, name='detalhes-ponto'),
	path('ponto/excluir/fechamento', ExcluirFechamentoView, name='excluir-fechamento'),
]
