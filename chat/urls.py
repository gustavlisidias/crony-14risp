from django.urls import path

from chat.views import ChatView, ChatUsersView, MesagemMassaView


urlpatterns = [
	path('chat/usuarios', ChatUsersView, name='chat-usuarios'),
	path('chat/iniciar/room/<int:index>/<str:tipo>', ChatView, name='chat-sala'),
	path('chat/nova/mensagem-massa', MesagemMassaView, name='mensagem-massa')
]
