from django.urls import path

from chat.consumers import ChatConsumer, ChatNotificationConsumer


websocket_urlpatterns = [
    path('ws/chat/room/<room>', ChatConsumer.as_asgi(), name='chat'),
	path('ws/chat/global/notifications', ChatNotificationConsumer.as_asgi(), name='chat-notifications'),
]