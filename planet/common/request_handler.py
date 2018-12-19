# -*- coding: utf-8 -*-
import os
import traceback
from collections import namedtuple

from itsdangerous import TimedJSONWebSignatureSerializer as Serializer, BadSignature, SignatureExpired
from flask import current_app, request

from .error_response import ApiError, BaseError, SystemError
from .success_response import Success


User = namedtuple('User', ('id', 'model', 'level'))


def request_first_handler(app):
    @app.before_request
    def token_to_user():
        current_app.logger.info('>>>>>>>>\n>>>>>>>>{}<<<<<<<<\n<<<<<<<<<<'.format('before request'))
        parameter = request.args.to_dict()
        token = parameter.get('token')
        if token:
            s = Serializer(current_app.config['SECRET_KEY'])
            try:
                data = s.loads(token)
                id = data['id']
                model = data['model']
                level = data['level']
                username = data.get('username', 'none')
                User = namedtuple('User', ('id', 'model', 'level', 'username'))
                user = User(id, model, level, username)
                setattr(request, 'user', user)
                current_app.logger.info('current_user info : {}'.format(data))
            except BadSignature as e:
                pass
            except SignatureExpired as e:
                pass
            except Exception as e:
                current_app.logger.info(e)
        current_app.logger.info(request.detail)
    #
    # @app.teardown_request
    # def end_request(param):
    #     end = """>>>>>>>>>>>>>>>>{}<<<<<<<<<<<<<<<<<<
    #
    #
    #     """
    #     current_app.logger.info(end.format('end  request'))
    #     return param



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


def gennerc_log(data, info='info'):
    """

    :param data: 'success get user %s, user id %s' %(user,userid)
    :param info:
    :return:
    """
    if isinstance(data, Exception):
        data = traceback.format_exc()
        info = 'bug'
    # current_app.logger.info('>>>>>>>>>>>>>>>>>>{}<<<<<<<<<<<<<<<<<<<'.format(info))

    if info == 'info':
        current_app.logger.info(data)
    else:
        current_app.logger.error(data)
    # try:
    #     current_app.logger.info(request.detail)
    # except Exception as e:
    #     current_app.logger.error(traceback.format_exc())


def check_mem():
    # 查看内存(M)
    import psutil
    process = psutil.Process(os.getpid())
    mem = process.memory_info()[0] / float(2 ** 20)
    current_app.logger.info('mem is %f ' % mem)
