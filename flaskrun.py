# -*- coding: utf-8 -*-
from planet import create_app
from planet.extensions.tasks import celery


app = create_app()

@app.route('/')
def hi():
    return 'ok'


if __name__ == '__main__':
    app.run(port=7443)
    # supervisord -c supervisord.conf
    # supervisorctl -c supervisord.conf shutdown
