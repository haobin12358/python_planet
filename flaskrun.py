# -*- coding: utf-8 -*-
import random

from flask import render_template

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



@socketio.on('connect', namespace='/test_conn')
def test_connect():
        socketio.emit('server_response',
                      {'data': 'connected'},namespace='/test_conn')


@socketio.on('connect', namespace='/change_num')
def change_num():
    # global thread
    # with thread_lock:
    # if thread is None:
    socketio.start_background_task(target=background_thread)


def background_thread():
    while True:
        socketio.sleep(5)
        t = random.randint(1, 100)
        socketio.emit('server_response',
                      {'data': t}, namespace='/change_num')


if __name__ == '__main__':
    # socketio.run(app, port=7443)
    app.run(port=7443)
    # supervisord -c supervisord.conf
    # supervisorctl -c supervisord.conf shutdown
