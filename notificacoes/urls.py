import notifications.urls

from django.urls import include, path

from notificacoes.ajax import LerNotificacaoView, LerTodasNotificacoesView, ExcluirNotificacaoView
from notificacoes.views import NotificacoesView, AdicionarNotificacaoView, EditarNotificacaoView


urlpatterns = [
	path('inbox/notifications/', include(notifications.urls, namespace='notifications')),
	
	path('notificacoes', NotificacoesView, name='notificacoes'),
	path('notificacoes/adicionar', AdicionarNotificacaoView, name='adicionar-notificacao'),
	path('notificacoes/excluir/<int:notid>', ExcluirNotificacaoView, name='excluir-notificacao'),
	path('notificacoes/editar/<int:notid>', EditarNotificacaoView, name='editar-notificacao'),

	path('notificacao/ler/<int:notid>', LerNotificacaoView, name='ler-notificacao'),
	path('notificacao/ler/todas', LerTodasNotificacoesView, name='ler-notificacoes'),
]
