# -*- coding: utf-8 -*-
import json
from datetime import datetime

from flask import current_app, Blueprint, Flask as _Flask, Request as _Request
from werkzeug.exceptions import HTTPException
from flask.json import JSONEncoder as _JSONEncoder
from flask_cors import CORS

from planet.api.v1.AFile import AFile
from planet.api.v1.AProduct import AProduct
from planet.api.v1.Acatogory import ACategory
from planet.common.error_response import ParamsError
from planet.common.request_handler import error_handler, request_first_handler
from planet.config.secret import DefaltSettig


class JSONEncoder(_JSONEncoder):
    """重写对象序列化, 当默认jsonify无法序列化对象的时候将调用这里的default"""
    def default(self, o):
        if hasattr(o, 'keys') and hasattr(o, '__getitem__'):
            res = dict(o)
            for k in res.keys():
                if k[0].isupper():
                    # 字段转小写
                    res[k.lower()] = res[k]
                    res.pop(k)
            return res
        if isinstance(o, datetime):
            # 也可以序列化时间类型的对象
            return o.strftime('%Y.%m.%d %H:%M:%S')
        if isinstance(o, type):
            raise o()
        if isinstance(o, HTTPException):
            raise o
        raise TypeError(repr(o) + " is not JSON serializable")


class Request(_Request):
    def on_json_loading_failed(self, e):
        if current_app is not None and current_app.debug:
            raise ParamsError('Failed to decode JSON object: {0}'.format(e))
        raise ParamsError('参数异常')

    def get_json(self, force=False, silent=False, cache=True):
        data = self.data
        if not data:
            return
        try:
            rv = json.loads(data)
        except ValueError as e:
            if silent:
                rv = None
                if cache:
                    normal_rv, _ = self._cached_json
                    self._cached_json = (normal_rv, rv)
            else:
                rv = self.on_json_loading_failed(e)
                if cache:
                    _, silent_rv = self._cached_json
                    self._cached_json = (rv, silent_rv)
        else:
            if cache:
                self._cached_json = (rv, rv)
        return rv

    @property
    def detail(self):
        return {
            'url': self.url,
            'method': self.method,
            'args': self.args.to_dict(),
            'data': self.data,
            'file': self.files,
        }


class Flask(_Flask):
    json_encoder = JSONEncoder
    request_class = Request


def register_v1(app):
    v1 = Blueprint(__name__, 'v1', url_prefix='/api/v1')
    v1.add_url_rule('/product/<string:product>', view_func=AProduct.as_view('product'))
    v1.add_url_rule('/file/<string:file>', view_func=AFile.as_view('file'))
    v1.add_url_rule('/category/<string:category>', view_func=ACategory.as_view('category'))
    # v1.add_url_rule.....
    app.register_blueprint(v1)


def create_app():
    app = Flask(__name__)
    app.config.from_object(DefaltSettig)
    register_v1(app)
    error_handler(app)
    CORS(app, supports_credentials=True)
    request_first_handler(app)
    return app

