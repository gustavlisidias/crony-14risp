from django.urls import path

from funcionarios.ajax import (
	AdicionarDocumentoView,
	ExcluirDocumentoView,
	ExcluirHistoricoJornadaView,
	RealoadDocumentosView,
	ExportarFuncionariosView,
	StreamDocumentoView,
	ExcluirEstabilidadeView,
	ConsultarFuncionarioView
)
from funcionarios.views import (
	AdicionarFuncionarioView,
	DocumentosView,
	EditarFuncionarioView,
	FuncionariosView,
	ImportarDocumentosView,
	FeedbackView,
	SolicitarFeedbackView,
	EnviarFeedbackView,
	ResponderFeedbackView,
	PerfilFuncionarioView,
	AlterarSenhaView
)


urlpatterns = [
	path('funcionarios', FuncionariosView, name='funcionarios'),
	path('funcionarios/adicionar', AdicionarFuncionarioView, name='adicionar-funcionario'),
	path('funcionarios/editar/<int:func>', EditarFuncionarioView, name='editar-funcionario'),
	path('funcionarios/exportar', ExportarFuncionariosView, name='exportar-funcionarios'),
	path('funcionarios/editar/<int:func>/excluir/historico-jornada/<int:agrupador>', ExcluirHistoricoJornadaView, name='excluir-historico-jornada'),
	path('funcionarios/excluir/estabilidade/<int:stab>', ExcluirEstabilidadeView, name='excluir-estabilidade'),
	path('funcionarios/consultar/codigo/<str:code>', ConsultarFuncionarioView, name='consultar-funcionario'),

	path('perfil', PerfilFuncionarioView, name='perfil'),
	path('perfil/alterar-senha', AlterarSenhaView, name='alterar-senha'),

	path('feedback', FeedbackView, name='feedback'),
	path('feedback/solicitacao', SolicitarFeedbackView, name='solicitar-feedback'),
	path('feedback/enviar', EnviarFeedbackView, name='enviar-feedback'),
	path('feedback/responder/<int:feed>', ResponderFeedbackView, name='responder-feedback'),

	path('documentos', DocumentosView, name='documentos'),
	path('documentos/adicionar', AdicionarDocumentoView, name='adicionar-documento'),
	path('documentos/importar', ImportarDocumentosView, name='importar-documentos'),
	path('documentos/atualizar/tabela', RealoadDocumentosView, name='reload-documentos'),
	path('documentos/excluir/<int:document>', ExcluirDocumentoView, name='excluir-documento'),
	path('documentos/stream/<int:document>/<str:model>/<str:norm>', StreamDocumentoView, name='stream-documento'),
]
