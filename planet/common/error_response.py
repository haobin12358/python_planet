# -*- coding: utf-8 -*-
from flask import json
from werkzeug.exceptions import HTTPException


class BaseError(HTTPException):
    message = '系统错误'
    status = 404
    status_code = 405001

    def __init__(self, message=None, status=None, status_code=None, header=None, *args, **kwargs):
        self.code = 200
        if message:
            self.message = message
        if status_code:
            self.status_code = status_code
        if status:
            self.status = status
        super(BaseError, self).__init__(message, None)

    def get_body(self, environ=None):
        body = dict(
            status=self.status,
            message=self.message,
            status_code=self.status_code
        )
        text = json.dumps(body)
        return text

    def get_headers(self, environ=None):
        return [('Content-Type', 'application/json')]

    @property
    def args(self):
        return self.message


class DbError(BaseError):
    message = '系统错误'
    status = 404


class DumpliError(BaseError):
    message = '重复数据'
    status = 404
    status_code = 405008


class ParamsError(BaseError):
    status = 405
    status_code = 405001
    message = '参数缺失'


class TokenError(BaseError):
    status = 405
    status_code = 405007
    message = "未登录"


class MethodNotAllowed(BaseError):
    status = 405
    status_code = 405002
    message = "方法不支持"


class AuthorityError(BaseError):
    status = 405
    status_code = 405003
    message = "无权限"


class NotFound(BaseError):
    status = 404
    status_code = 405004
    message = '无此项目'


class SystemError(BaseError):
    status_code = 405005
    message = '系统错误'
    status = 405


class ApiError(BaseError):
    status = 405
    status_code = 405006
    message = "接口未注册"


class TimeError(BaseError):
    status = 405
    status_code = 405009
    message = "敬请期待"


class PoorScore(BaseError):
    status = 405
    status_code = 405010
    message = '积分不足'


class StatusError(BaseError):
    status = 405
    status_code = 405011
    message = '状态不正确'


class WXLoginError(BaseError):
    status = 405
    status_code = 405012
    message = '微信登录失败'
