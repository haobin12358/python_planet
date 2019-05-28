# -*- coding: utf-8 -*-
import random

from flask import render_template, request, session

from planet import create_app, socketio
from planet.extensions.tasks import celery
# from threading import Lock

# thread = None
# thread_lock = Lock()

app = create_app()


@app.route('/api/v2/test')
def hi():
    #     return 'ok'
    return render_template('index.html')


@app.route('/api/v2/mes')
def mes():
    #     return 'ok'
    event_name = 'test'
    data = request.args.get("msg")
    broadcasted_data = {'data': data}
    print("publish msg==>", broadcasted_data)
    socketio.emit(event_name, broadcasted_data, broadcast=True)
    return 'send msg successful!'


@socketio.on('json')
def handle_json(json):
    print(session.get('id'))
    # session['id'] = 'json'
    print('received json: ' + str(json))


@socketio.on('message')  # 接收匿名send消息
def message_handler(*args):
    print(session.get('id'))
    # session['id'] = 'message'
    print('recive {0} data from client'.format(type(args[0])), args)
    return args

sids = []


if __name__ == '__main__':
    # app.
    socketio.run(app, port=7443)

    # app.run(port=7443)
    # supervisord -c supervisord.conf
    # supervisorctl -c supervisord.conf shutdown
