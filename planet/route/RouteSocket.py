from flaskrun import socketio
from planet.models import UserPlatfromMessage

@socketio.on('connect')
def connect(token):
    pass