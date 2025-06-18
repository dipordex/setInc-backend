# socket_instance.py
import socketio

# Create async Socket.IO server instance
sio = socketio.AsyncServer(async_mode='asgi', cors_allowed_origins='*')

# Optional: Store sessions, rooms, user mappings here
connected_users = {}  # Example: { user_id: set(sids) }


@sio.event
async def connect(sid, environ):
    # Extract user ID from query string or headers
    query = environ.get('QUERY_STRING', '')
    from urllib.parse import parse_qs
    user_id = parse_qs(query).get('user_id', [None])[0]

    if user_id:
        await sio.save_session(sid, {"user_id": user_id})
        await sio.enter_room(sid, str(user_id))  # Room name = user_id
        connected_users.setdefault(user_id, set()).add(sid)
        print(f"[Socket] User {user_id} connected with SID {sid}")
        await sio.emit('connected', {'msg': 'Welcome'}, to=sid)
    else:
        print("[Socket] Connection rejected: No user_id provided")
        await sio.disconnect(sid)


@sio.event
async def disconnect(sid):
    session = await sio.get_session(sid)
    user_id = session.get("user_id")
    print(f"[Socket] SID {sid} disconnected for user {user_id}")
    if user_id and user_id in connected_users:
        connected_users[user_id].discard(sid)
        if not connected_users[user_id]:
            del connected_users[user_id]


@sio.event
async def ping(sid, data):
    await sio.emit("pong", {"msg": "pong"}, to=sid)
