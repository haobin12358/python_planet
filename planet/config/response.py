# *- coding:utf8 *-
from WeiDian.common.base_error import BaseError


class PARAMS_MISS(BaseError):
    status = 405
    status_code = 405001
    message = '参数缺失'

class PARAMS_ERROR(BaseError):
    status = 405
    status_code = 405001
    message = '参数错误'

class PARAMS_REDUNDANCE(BaseError):
    status= 405
    status_code= 405003
    message= "参数冗余"


class TOKEN_ERROR(BaseError):
    status = 405
    status_code = 403001
    message = "未登录"


class MethodNotAllowed(BaseError):
    status = 405
    status_code = 405002
    message = "方法不支持"


class AUTHORITY_ERROR(TOKEN_ERROR):
    message = "无权限"


class SYSTEM_ERROR(BaseError):
    status_code = 200
    message = '系统错误'
    status = 404

class NOT_FOUND(BaseError):
    status_code = 200
    message = '对象不存在'
    status = 404

class APIS_WRONG(BaseError):
    status = 405
    status_code = 405002
    message = "接口未注册"


class TIME_ERROR(BaseError):
    status = 405
    status_code = 405003
    message = "敬请期待"


class NETWORK_ERROR(BaseError):
    status = 405
    status_code = 405004
    message = '网络异常'


class DumpliError(BaseError):
    status = 405
    status_code = 405005
    message = '重复数据'

