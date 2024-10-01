from django.urls import path

from agenda.ajax import (
    AprovarSolicitacaoFeriasView,
    EditarEventoView,
    ExcluirSolicitacaoFeriasView,
    MoverEventoView,
    ProcurarDocumentosFeriasView,
)
from agenda.views import (
    AdicionarAtividadeView,
    AgendaView,
    FeriasView,
    DesempenhoView,
    AdicionarAvaliacaoView,
)


urlpatterns = [
    path('agenda', AgendaView, name='agenda'),
    path('agenda/adicionar', AdicionarAtividadeView, name='adicionar-evento'),
    path('agenda/mover', MoverEventoView, name='mover-evento'),
    path('agenda/editar', EditarEventoView, name='editar-evento'),
	
    path('ferias', FeriasView, name='ferias'),
    path('ferias/procurar/documentos/<int:solic>', ProcurarDocumentosFeriasView, name='procurar-documentos'),
    path('ferias/excluir/solicitacao/<int:solic>', ExcluirSolicitacaoFeriasView, name='excluir-solicitacao-ferias'),
    path('ferias/aprovar/solicitacao/<int:solic>', AprovarSolicitacaoFeriasView, name='aprovar-solicitacao-ferias'),

    path('desempenho', DesempenhoView, name='desempenho'),
    path('desempenho/avaliar/atividade/<int:atvid>', AdicionarAvaliacaoView, name='desempenho-avaliacao'),
]
