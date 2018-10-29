# -*- coding: utf-8 -*-
from planet import create_app

app = create_app()


@app.route('/')
def hi():
    return 'ok'


if __name__ == '__main__':
    app.run(port=7443)
