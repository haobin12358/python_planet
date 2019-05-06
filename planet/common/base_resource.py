# -*- coding: utf-8 -*-
from flask import request, jsonify
from flask.views import MethodView
from werkzeug.wrappers import Response

from .error_response import ApiError, MethodNotAllowed


class Resource(MethodView):

    def dispatch_request(self, *args, **kwargs):
        meth = getattr(self, request.method.lower(), None)
        if meth is None and request.method == 'HEAD':
            meth = getattr(self, 'get', None)
        assert meth is not None, 'Unimplemented method %r' % request.method
        apis = meth(*args, **kwargs)
        # if not isinstance(apis, dict):
        #     return super(Resource, self).dispatch_request(*args, **kwargs)
        for kwarg in kwargs.values():
            if kwarg not in apis:
                raise ApiError(u'接口未注册 | api:{} | request_method: {}'.format(request.path,
                                                                             request.environ['REQUEST_METHOD']))
            data = apis[kwarg]()
            if isinstance(data, Response) or isinstance(data, str):
                return data
            return jsonify(data)
        return apis

    def get(self, *args, **kwargs):
        raise MethodNotAllowed()

    def post(self, *args, **kwargs):
        raise MethodNotAllowed()

    def option(self, *args, **kwargs):
        raise MethodNotAllowed()

    def put(self, *args, **kwargs):
        raise MethodNotAllowed()

    def delete(self, *args, **kwargs):
        raise MethodNotAllowed()


