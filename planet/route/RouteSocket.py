import ast
import random
from threading import Lock

from flask import session, request

# from flaskrun import socketio
from flask_socketio import Namespace, emit, join_room, leave_room

from planet.extensions.register_ext import conn
from planet.models import UserPlatfromMessage

thread = None
thread_lock = Lock()


def background_thread(socketio):
    while True:
        # 该方法无法带session
        socketio.sleep(5)

        t = random.randint(1, 100)
        # print(session.get('id'), t)
        print(t)
        # self.socketio.emit('server_response', {'data': t})
        socketio.emit('server_response', {'data': t}, )


class Mynamespace(Namespace):
    # def __init__(self, socketio):
    #     self.socketio = socketio
    #
    #     self.socketio.on_event('setsession', self.connect)
    #     self.socketio.on_event('my event', self.my_event)
    #     self.socketio.on_event('change num', self.change_num)

    def on_setsession(self, token):
        from planet.common.request_handler import token_to_user_
        print(token)
        user = token_to_user_(token)
        print(user)
        sids = conn.get('sids')
        print('get sids', sids)
        print('get connect sid ', request.sid)
        # from flaskrun import sids
        if not sids:
            conn.set('sids', [request.sid])
        else:
            sids = ast.literal_eval(str(sids, encoding='utf-8'))
            print('pre append ', sids)
            sids.append(request.sid)
            print('after ', sids)
            conn.set('sids', sids)
        # join_room(request.sid)

        if user:

            session['id'] = user.id
            session['username'] = user.username

            return '{} is connect '.format(user.username)
            # conn.set('sid', session.sid)
        else:
            # session['id'] = 'random'
            # session['username'] = 'unknown'
            # conn.set('')
            return '{} is connect '.format('unknown')

    # @self.socketio.on('my event')  # 接收emit 的 myevent 消息
    def on_my_event(self, data):
        print(data)
        print(session.get('id'))
        # session['id'] = 'json'
        return 'my event received'

    # @socketio.on('connect', namespace='/test_conn')
    # def test_connect():
    #         socketio.emit('server_response',
    #                       {'data': 'connected'},namespace='/test_conn')

    #
    # @socketio.on('connect', namespace='/change_num')

    def on_change_num(self, data):
        print(data)
        print(session.get('id'))
        roomid = data.get('room') or request.sid
        # global thread
        # with thread_lock:
        #     if thread is None:
        #         thread = self.socketio.start_background_task(target=background_thread, socketio=self.socketio)

        t = random.randint(1, 100)
        self.socketio.emit('server_response', {'data': t}, room=roomid)

    # def on_disconnect(self, data):
    #     print('get data')
    #     print(session.get('id'))
    #     sid = request.sid
    #     from flaskrun import sids
    #     if sid in sids:
    #         sids.remove(sid)
    #     # leave_room(sid)
    #     username = session.get('username')
    #     return '{} is dis connect'.format(username)

# @app.route('/api/v2/mes')
# def mes():
#     #     return 'ok'
#     event_name = 'test'
#     data = request.args.get("msg")
#     broadcasted_data = {'data': data}
#     print("publish msg==>", broadcasted_data)
#     socketio.emit(event_name, broadcasted_data, broadcast=True)
#     return 'send msg successful!'
