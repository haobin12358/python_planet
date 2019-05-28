import ast
import json
import random
from threading import Lock

from flask import request

from datetime import datetime, date
from decimal import Decimal

# from flaskrun import socketio
from flask_socketio import Namespace, join_room, leave_room

from werkzeug.exceptions import HTTPException
from flask.json import JSONEncoder as _JSONEncoder

# from planet import JSONEncoder
from planet.common.error_response import AuthorityError
from planet.common.success_response import Success
# from planet.control.BaseControl import JSONEncoder
from planet.extensions.register_ext import conn
# from planet.models import UserPlatfromMessage

thread = None
thread_lock = Lock()


class JSONEncoder(_JSONEncoder):
    """重写对象序列化, 当默认jsonify无法序列化对象的时候将调用这里的default"""
    def default(self, o):

        if hasattr(o, 'keys') and hasattr(o, '__getitem__'):
            res = dict(o)
            new_res = {k.lower(): v for k, v in res.items()}
            return new_res
        if isinstance(o, datetime):
            # 也可以序列化时间类型的对象
            return o.strftime('%Y-%m-%d %H:%M:%S')
        if isinstance(o, date):
            return o.strftime('%Y-%m-%d')
        if isinstance(o, type):
            raise o()
        if isinstance(o, HTTPException):
            return o.get_body()
        if isinstance(o, Decimal):
            return round(float(o), 2)
        raise TypeError(repr(o) + " is not JSON serializable")


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
        usersid = conn.get('usersid')
        print('get sids', usersid)
        print('get connect sid ', request.sid)
        # from flaskrun import sids

        # join_room(request.sid)

        if user:
            sessiondict = {user.id: request.sid}
            if not usersid:
                conn.set('usersid', sessiondict)
            else:
                usersid = ast.literal_eval(str(usersid, encoding='utf-8'))
                print('pre append ', usersid)
                # sids.append(request.sid)
                usersid.update(sessiondict)
                print('after ', usersid)
                conn.set('sids', usersid)

            return json.loads(json.dumps(Success('{} is connect '.format(user.username)), cls=JSONEncoder))
            # conn.set('sid', session.sid)
        # else:
        #     # session['id'] = 'random'
        #     # session['username'] = 'unknown'
        #     # conn.set('')
        #     return '{} is connect '.format('unknown')
        raise AuthorityError('token 失效')

    # @self.socketio.on('my event')  # 接收emit 的 myevent 消息
    def on_my_event(self, data):
        print(data)
        # print(session.get('id'))
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
        # print(session.get('id'))
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
