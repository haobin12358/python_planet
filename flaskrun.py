# -*- coding: utf-8 -*-
import random

from flask import render_template, request

from planet import create_app
from planet.extensions.tasks import celery
# from threading import Lock

# thread = None
# thread_lock = Lock()

app, socketio = create_app()


@app.route('/')
def hi():
    #     return 'ok'
    return render_template('index.html')

#
# @socketio.on('connect', namespace='/test_conn')
# def test_connect():
#         socketio.emit('server_response',
#                       {'data': 'connected'},namespace='/test_conn')

#
# @socketio.on('connect', namespace='/change_num')
# def change_num():
#     # global thread
#     # with thread_lock:
#     # if thread is None:
#     socketio.start_background_task(target=background_thread)
#
#
# def background_thread():
#     while True:
#         socketio.sleep(5)
#         t = random.randint(1, 100)
#         socketio.emit('server_response',
#                       {'data': t}, namespace='/change_num')


@socketio.on('json')
def handle_json(json):
    print('received json: ' + str(json))


@socketio.on('message')  # 接收匿名send消息
def message_handler(*args):
    print('recive {0} data from client'.format(type(args[0])), args)
    return args


@socketio.on('my event')  # 接收emit 的 myevent 消息
def my_event(data):
    print(data)
    return 'my event received'


if __name__ == '__main__':
    socketio.run(app, port=7443)
    # app.run(port=7443)
    # supervisord -c supervisord.conf
    # supervisorctl -c supervisord.conf shutdown
