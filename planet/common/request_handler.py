# -*- coding: utf-8 -*-
import logging
import os
import sys
import traceback
from collections import namedtuple
from datetime import datetime
from logging.handlers import TimedRotatingFileHandler

from itsdangerous import TimedJSONWebSignatureSerializer as Serializer, BadSignature, SignatureExpired
from flask import current_app, request

from .error_response import ApiError, BaseError, SystemError
from .success_response import Success
from ..config.cfgsetting import singleton

User = namedtuple('User', ('id', 'model', 'level'))


def request_first_handler(app):
    @app.before_request
    def token_to_user():
        gennerc_log('before request', info='info')
        parameter = request.args.to_dict()
        token = parameter.get('token')
        s = Serializer(current_app.config['SECRET_KEY'])
        try:
            data = s.loads(token)
            id = data['id']
            model = data['model']
            level = data['level']
            User = namedtuple('User', ('id', 'model', 'level'))
            user = User(id, model, level)
            setattr(request, 'user', user)
        except BadSignature as e:
            pass
        except SignatureExpired as e:
            pass
        except Exception as e:
            pass


def error_handler(app):
    @app.errorhandler(404)
    def error404(e):
        return ApiError(u'接口未注册' + request.path)

    @app.errorhandler(Exception)
    def framework_error(e):
        if isinstance(e, Success):
            return e
        gennerc_log(e)
        if isinstance(e, BaseError):
            return e
        else:
            if app.config['DEBUG']:
                return SystemError(e.args)
            return SystemError()


def gennerc_log(data, info='bug'):
    if isinstance(data, Exception):
        data = traceback.format_exc()
    current_app.logger.info('>>>>>>>>>>>>>>>>>>{}<<<<<<<<<<<<<<<<<<<'.format(info))
    current_app.logger.error(data)
    try:
        current_app.logger.info(request.detail)
    except Exception as e:
        pass


def check_mem():
    # 查看内存(M)
    import psutil
    process = psutil.Process(os.getpid())
    mem = process.memory_info()[0] / float(2 ** 20)
    current_app.logger.info('mem is %f ' % mem)
