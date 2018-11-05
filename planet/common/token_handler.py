# -*-LJ_DB_PWi coding: utf-8 -*-
from itsdangerous import TimedJSONWebSignatureSerializer as Serializer, BadSignature, SignatureExpired
from flask import current_app, request

from .error_response import AuthorityError, TokenError
from .success_response import Success
from ..config.http_config import API_HOST
from ..config.secret import wxscope, appid, appsecret
from ..extensions.weixin import WeixinLogin


def usid_to_token(id, model='User', level=0, expiration=''):
    """生成令牌
    id: 用户id
    model: 用户类型(User 或者 SuperUser)
    expiration: 过期时间, 在appcommon/setting中修改
    """
    if not expiration:
        expiration = current_app.config['TOKEN_EXPIRATION']
    s = Serializer(current_app.config['SECRET_KEY'], expires_in=expiration)
    return s.dumps({
        'id': id,
        'model': model,
        'level': level
    })


def is_admin():
    """是否是管理员"""
    return hasattr(request, 'user') and request.user.model == u'Admin'


def is_tourist():
    """是否是游客"""
    return not hasattr(request, 'user')


def common_user():
    """是否是普通用户, 不包括管理员"""
    return hasattr(request, 'user') and request.user.model == u'user'


def is_hign_level_admin():
    """高级管理员, 包括高级和超级"""
    return is_admin() and request.user.level > 0


def admin_required(func):
    def inner(self, *args, **kwargs):
        if not is_admin():
            raise AuthorityError()
        return func(self, *args, **kwargs)
    return inner


def is_agent():
    """是否是代理商"""
    return hasattr(request, 'user') and request.user.level == 2


def token_required(func):
    def inner(self, *args, **kwargs):
        parameter = request.args.to_dict()
        token = parameter.get('token')
        s = Serializer(current_app.config['SECRET_KEY'])
        try:
            data = s.loads(token)
        except BadSignature as e:
            # 签名出错的token
            return func(self, *args, **kwargs)
        except SignatureExpired as e:
            # 过期的token
            return func(self, *args, **kwargs)
        except Exception as e:
            # 无法解析的token
            return func(self, *args, **kwargs)
        id = data['id']
        time = data['time']
        model = data['model']
        if model != 'User' and model != 'Admin':
            return func(self, *args, **kwargs)

        sessions = db_session()
        try:
            if model == 'User':
                from WeiDian.models.model import User
                user = sessions.query(User).filter_by(USid=id).first()
                if not user:
                    # 不存在的用户
                    return func(self, *args, **kwargs)
                user.id = user.USid
                user.scope = 'User'
                user.level = user.USlevel
            if model == 'SuperUser':
                from WeiDian.models.model import SuperUser
                user = sessions.query(SuperUser).filter_by(SUid=id).first()
                if not user:
                    # 不存在的管理
                    return func(self, *args, **kwargs)
                user.id = user.SUid
                user.scope = 'SuperUser'
                user.level = user.SUlevel
            sessions.expunge_all()
            sessions.commit()
            if user:
                request.user = user
            return func(self, *args, **kwargs)
        finally:
            sessions.close()
        if not is_tourist():
            return func(self, *args, **kwargs)
        raise TokenError()
        # state_url = request.environ.get('HTTP_X_URL', request.url)
        # if '#' in state_url:
        #     state_url = state_url.replace('#', '$')
        # state = str(state_url)
        # self.login = WeixinLogin(appid, appsecret)
        # redirect_url = self.login.authorize(API_HOST + "/api/v1/user/weixin_callback", wxscope, state=state)
        # return Success(u'执行跳转', status=302, data={
        #     'redirect_url': redirect_url
        # })
    return inner






