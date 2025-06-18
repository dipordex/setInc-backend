import os
import django
from django.core.asgi import get_asgi_application

from socket_instance import sio  # Custom shared Socket.IO server instance
from socketio import ASGIApp

# Set Django settings
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'setinc.settings')
django.setup()

# Django ASGI app
django_asgi_app = get_asgi_application()

# Wrap Django app with Socket.IO
application = ASGIApp(sio, other_asgi_app=django_asgi_app)
