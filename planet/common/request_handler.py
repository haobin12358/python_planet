# -*- coding: utf-8 -*-
import logging
import os
import traceback
from collections import namedtuple
from datetime import datetime

from itsdangerous import TimedJSONWebSignatureSerializer as Serializer, BadSignature, SignatureExpired
from flask import current_app, request

from .error_response import ApiError, BaseError, SystemError
from .success_response import Success

User = namedtuple('User', ('id', 'model', 'level'))


def request_first_handler(app):
    @app.before_request
    def token_to_user():
        generic_error_log('before request', info='info')
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
        generic_error_log(e)
        if isinstance(e, BaseError):
            return e
        else:
            return SystemError()


def generic_error_log(data, path='flask', info='bug'):
    logger_file_name = datetime.now().strftime("%Y-%m-%d") + '.log'
    logger_dir = os.path.join(current_app.config['BASEDIR'], 'logs', path)
    if not os.path.isdir(logger_dir):
        os.makedirs(logger_dir)
    logger_file = os.path.join(logger_dir, logger_file_name)
    handler = logging.FileHandler(logger_file)
    if isinstance(data, Exception):
        data = traceback.format_exc()
    logging_format = logging.Formatter(
        "%(asctime)s - %(filename)s \n %(message)s"
        )
    handler.setFormatter(logging_format)
    handler.setLevel(logging.INFO)
    current_app.logger.addHandler(handler)
    current_app.logger.info('>>>>>>>>>>>>>>>>>>{}<<<<<<<<<<<<<<<<<<<'.format(info))
    current_app.logger.error(data)
    try:
        current_app.logger.info(request.detail)
    except Exception as e:
        pass
    finally:
        current_app.logger.removeHandler(handler)
