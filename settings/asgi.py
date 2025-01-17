# ruff: noqa: E402
import os
import django
import sys

from pathlib import Path
from dotenv import load_dotenv

load_dotenv(os.path.join(Path(__file__).resolve().parent.parent, '.env'))
sys.path.append(os.getenv('SYSTEM_PATH'))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'settings.settings')
django.setup()

from channels.auth import AuthMiddlewareStack
from channels.routing import ProtocolTypeRouter, URLRouter
from channels.security.websocket import AllowedHostsOriginValidator

from django.core.asgi import get_asgi_application

from settings.routing import websocket_urlpatterns


django_asgi_app = get_asgi_application()

application = ProtocolTypeRouter(
	{
		'http': django_asgi_app,
		'websocket': AllowedHostsOriginValidator(
			AuthMiddlewareStack(URLRouter(websocket_urlpatterns))
		),
	}
)