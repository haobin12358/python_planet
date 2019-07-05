# -*- coding: utf-8 -*-
from planet import create_app, socketio
from planet.extensions.tasks import celery

app = create_app()


if __name__ == '__main__':
    # app.
    # socketio.run(app, port=7443)

    app.run(port=7443)
    # supervisord -c supervisord.conf
    # supervisorctl -c supervisord.conf shutdown
