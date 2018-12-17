# -*-coding: utf-8 -*-
from itsdangerous import TimedJSONWebSignatureSerializer as Serializer
from flask import current_app, request

from .error_response import AuthorityError, TokenError


def usid_to_token(id, model='User', level=0, expiration='', username='none'):
    """生成令牌
    id: 用户id
    model: 用户类型(User 或者 Admin, Supplizer)
    expiration: 过期时间, 在config/secret中修改
    """
    if not expiration:
        expiration = current_app.config['TOKEN_EXPIRATION']
    s = Serializer(current_app.config['SECRET_KEY'], expires_in=expiration)
    return s.dumps({
        'username': username,
        'id': id,
        'model': model,
        'level': level,

    }).decode()


def is_admin():
    """是否是管理员"""
    return hasattr(request, 'user') and request.user.model == 'Admin'


def is_supplizer():
    return hasattr(request, 'user') and request.user.model == 'Supplizer'


def is_tourist():
    """是否是游客"""
    return not hasattr(request, 'user')


def common_user():
    """是否是普通用户, 不包括管理员"""
    return hasattr(request, 'user') and request.user.model == 'User'


def is_shop_keeper():
    """是否是店主 todo"""
    return common_user() and request.user.level == 2


def is_hign_level_admin():
    """超级管理员"""
    return is_admin() and request.user.level == 1


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
        raise TokenError()
    return inner


def get_current_user():
    usid = request.user.id
    from planet.models import User
    return User.query.filter(User.USid == usid, User.isdelete == False).first()


def get_current_admin():
    adid = request.user.id
    from planet.models import Admin
    return Admin.query.filter(Admin.ADid == adid, Admin.isdelete == False).first()






