from django.urls import path

from agenda.ajax import (
    AlterarSolicitacaoFeriasView,
    EditarEventoView,
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
    path('ferias/alterar/solicitacao/<int:solic>', AlterarSolicitacaoFeriasView, name='alterar-solicitacao-ferias'),

    path('desempenho', DesempenhoView, name='desempenho'),
    path('desempenho/avaliar/atividade/<int:atvid>', AdicionarAvaliacaoView, name='desempenho-avaliacao'),
]
