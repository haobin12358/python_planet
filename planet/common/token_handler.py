# -*-LJ_DB_PWi coding: utf-8 -*-
from itsdangerous import TimedJSONWebSignatureSerializer as Serializer
from flask import current_app, request

from .error_response import AuthorityError
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


def token_required(func):
    def inner(self, *args, **kwargs):
        if not is_tourist():
            return func(self, *args, **kwargs)
        state_url = request.environ.get('HTTP_X_URL', request.url)
        if '#' in state_url:
            state_url = state_url.replace('#', '$')
        state = str(state_url)
        self.login = WeixinLogin(appid, appsecret)
        redirect_url = self.login.authorize(API_HOST + "/api/v1/user/weixin_callback", wxscope, state=state)
        return Success(u'执行跳转', status=302, data={
            'redirect_url': redirect_url
        })
    return inner






