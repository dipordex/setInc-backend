import os
import django
import socketio
from django.core.asgi import get_asgi_application
from socketio import ASGIApp

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'setinc.settings')
django.setup()

# Create Async Socket.IO Server
sio = socketio.AsyncServer(async_mode='asgi', cors_allowed_origins='*')

# Django ASGI App
django_asgi_app = get_asgi_application()

# Wrap Django app with Socket.IO ASGI app
application = ASGIApp(sio, other_asgi_app=django_asgi_app)


@sio.event
async def connect(sid, environ):
    print(f"Socket connected: {sid}")
    await sio.emit('welcome', {'msg': 'Hello'}, to=sid)

@sio.event
async def disconnect(sid):
    print(f"Socket disconnected: {sid}")

@sio.event
async def my_event(sid, data):
    print(f"Received event: {data}")
    await sio.emit('response', {'msg': 'Got it!'}, to=sid)
