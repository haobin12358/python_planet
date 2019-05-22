# -*- coding: utf-8 -*-
import os
import re
import traceback
import uuid
from collections import namedtuple

from itsdangerous import TimedJSONWebSignatureSerializer as Serializer, BadSignature, SignatureExpired
from flask import current_app, request
from sqlalchemy.exc import IntegrityError

from planet.extensions.register_ext import db
from planet.models import UserLoginApi
from .error_response import ApiError, BaseError, SystemError, DumpliError
from .success_response import Success


User = namedtuple('User', ('id', 'model', 'level'))


def _get_user_agent():
    user_agent = request.user_agent
    ua = str(user_agent).split()
    osversion = phonemodel = wechatversion = nettype = None
    if not re.match(r'^(android|iphone)$', str(user_agent.platform)):
        return
    for index, item in enumerate(ua):
        if 'Android' in item:
            osversion = f'Android {ua[index + 1][:-1]}'
            phonemodel = ua[index + 2]
            temp_index = index + 3
            while 'Build' not in ua[temp_index]:
                phonemodel = f'{phonemodel} {ua[temp_index]}'
                temp_index += 1
        elif 'OS' in item:
            if ua[index - 1] == 'iPhone':
                osversion = f'iOS {ua[index + 1]}'
                phonemodel = 'iPhone'
        if 'MicroMessenger' in item:
            try:
                wechatversion = item.split('/')[1]
                if '(' in wechatversion:
                    wechatversion = wechatversion.split('(')[0]
            except Exception as e:
                current_app.logger.error('MicroMessenger:{}, error is :{}'.format(item, e))
                wechatversion = item.split('/')[1][:3]
        if 'NetType' in item:
            nettype = re.match(r'^(.*)\/(.*)$', item).group(2)
    return osversion, phonemodel, wechatversion, nettype, user_agent.string

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
                useragent = _get_user_agent()
                if useragent:
                    with db.auto_commit():
                        ula_dict1 = {
                            'ULAid': str(uuid.uuid1()),
                            'USid': request.user.id,
                            'ULA':request.detail['path'],
                            'USTip':request.remote_addr,
                            'OSVersion':useragent[0],
                            'PhoneModel':useragent[1],
                            'WechatVersion':useragent[2],
                            'NetType':useragent[3]
                        }
                        current_app.logger.info('ula info : {}'.format(ula_dict1))
                        ula_instance = UserLoginApi.create(ula_dict1)
                        db.session.add(ula_instance)

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
    #
    # @app.errorhandler(IntegrityError)
    # def dumpli_error(e):
    #     return DumpliError()


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
