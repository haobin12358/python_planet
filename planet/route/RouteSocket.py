import ast
import json
import random
from threading import Lock

from flask import request, session, current_app

from datetime import datetime, date
from decimal import Decimal

# from flaskrun import socketio
from flask_socketio import Namespace, join_room, leave_room, emit, disconnect

from werkzeug.exceptions import HTTPException
from flask.json import JSONEncoder as _JSONEncoder

# from planet import JSONEncoder
from planet.common.error_response import AuthorityError, ParamsError
from planet.common.success_response import Success
# from planet.control.BaseControl import JSONEncoder
from planet.config.enums import UserMessageTyep
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
            return json.loads(o.get_body())
        if isinstance(o, Decimal):
            return round(float(o), 2)
        raise TypeError(repr(o) + " is not JSON serializable")


def return_res(res):
    if isinstance(res, HTTPException):
        return json.loads(json.dumps(res, cls=JSONEncoder))
    return res


def background_thread(socketio):
    while True:
        # 该方法无法带session
        socketio.sleep(5)

        t = random.randint(1, 100)
        # current_app.logger.info(session.get('id'), t)
        current_app.logger.info(t)
        # emit('server_response', {'data': t})
        socketio.emit('server_response', {'data': t}, )


class Mynamespace(Namespace):
    def on_setsession(self, token):
        from planet.common.request_handler import token_to_user_
        current_app.logger.info(token)
        user = token_to_user_(token)
        current_app.logger.info(user)
        usersid = conn.get('usersid')
        current_app.logger.info('get sids', usersid)
        current_app.logger.info('get connect sid ', request.sid)
        # from flaskrun import sids
        current_app.logger.info('request ', request.headers, )

        # join_room(request.sid)

        if user:
            sessiondict = {user.id: request.sid}
            # 创建session
            session.update({'id': user.id})

            if not usersid:
                conn.set('usersid', sessiondict)
            else:
                usersid = ast.literal_eval(str(usersid, encoding='utf-8'))
                current_app.logger.info('pre append ', usersid)
                # sids.append(request.sid)
                usersid.update(sessiondict)
                current_app.logger.info('after ', usersid)
                conn.set('usersid', usersid)
            # res = json.loads(json.dumps(Success('{} is connect '.format(user.username)), cls=JSONEncoder))
            # current_app.logger.info(res, type(res))
            # res = json.loads(Success('{} is connect '.format(user.username)), cls=JSONEncoder)
            # current_app.logger.info(res, type(res))
            # self.socketio.emit('server_response', Success('{} is connect '.format(user.username)))
            emit('server_response', Success('{} is connect '.format(user.username)))

            return return_res(Success('{} is connect '.format(user.username), data=user.id))

            # conn.set('sid', session.sid)
        # else:
        #     # session['id'] = 'random'
        #     # session['username'] = 'unknown'
        #     # conn.set('')
        #     return '{} is connect '.format('unknown')
        # self.socketio.emit('server_response', AuthorityError('token 失效'))
        emit('server_response', AuthorityError('token 失效'))
        return return_res(AuthorityError('token 失效'))

    # @self.socketio.on('my event')  # 接收emit 的 myevent 消息
    def on_my_event(self, data):
        current_app.logger.info(data)
        # current_app.logger.info(session.get('id'))
        # session['id'] = 'json'
        return 'my event received'

    # @socketio.on('connect', namespace='/test_conn')
    # def test_connect():
    #         socketio.emit('server_response',
    #                       {'data': 'connected'},namespace='/test_conn')

    #
    # @socketio.on('connect', namespace='/change_num')

    def on_change_num(self, data):
        current_app.logger.info(data)
        # current_app.logger.info(session.get('id'))
        roomid = data.get('room') or request.sid
        # global thread
        # with thread_lock:
        #     if thread is None:
        #         thread = self.socketio.start_background_task(target=background_thread, socketio=self.socketio)

        t = random.randint(1, 100)
        # emit('server_response', {'data': t}, room=roomid)
        self.socketio.emit('server_response', {'data': t}, room=roomid)

    def on_get_message(self):
        from planet.control.CMessage import CMessage
        cmsg = CMessage()
        userid = session.get('id')
        current_app.logger.info('get current user {}'.format(userid))
        usersids = cmsg.get_usersid()
        usersid = usersids.get(userid)
        if usersid != request.sid:
            # todo 重新连接更新redis
            pass
        cmsg.push_platform_message(None, userid, usersid)

    def on_disconnect(self):
        current_app.logger.info(session.get('id'))
        current_app.logger.info('{} is dis connect'.format(session.get('id')))
        disconnect()

    def on_my_ping(self):
        self.socketio.emit('my_pong', Success)

    def on_disconnect_request(self):
        # session['receive_count'] = session.get('receive_count', 0) + 1
        # emit('my_response',
        #      {'data': 'Disconnected!', 'count': session['receive_count']})
        disconnect()

    def on_join_room(self, data):
        # data 是roomid
        current_app.logger.info(data)
        userid = session.get('id')
        current_app.logger.info('start join room', userid)
        if not userid:
            return return_res(AuthorityError)
        from planet.control.CMessage import CMessage
        cmsg = CMessage()
        roomid = cmsg.get_room(data, userid)
        join_room(roomid, request.sid)
        return return_res(Success(data=roomid))

    def on_send_msg(self, data):
        current_app.logger.info(data)
        userid = session.get('id')

        current_app.logger.info('send message', userid)
        if not userid:
            return return_res(AuthorityError)
        roomid = data.get('roid')
        message = data.get('umsgtext')
        umsgtype = data.get('umsgtype') or 0
        try:
            umsgtype = UserMessageTyep(int(umsgtype)).value
        except:
            umsgtype = 0

        if message == "":
            return return_res(ParamsError('内容不能为空'))

        from planet.control.CMessage import CMessage
        cmsg = CMessage()
        umsg = cmsg.send_msg(message, umsgtype, roomid, userid)
        current_app.logger.info('写入成功')
        self.socketio.emit('new_message', umsg, room=roomid)
        current_app.logger.info('发送成功')
        return return_res(Success('发送成功'))

    # def on_notice(self):
    def on_read_message(self, data):
        current_app.logger.info(data)
        userid = session.get('id')

        current_app.logger.info('send message', userid)
        if not userid:
            return return_res(AuthorityError)
        umsgid = data.get('umsgid')
        from planet.control.CMessage import CMessage
        cmsg = CMessage()
        cmsg._read_message(umsgid, userid)
        return return_res(Success('已读'))
