# -*- coding: utf-8 -*-
import re

from flask import request

from .error_response import ParamsError


def parameter_required(required=None, others='allow', filter_none=True, forbidden=None, datafrom=None):
    """验证请求中必需的参数
    others: 如果是allow, 则代表不会清除其他参数
    filter_none: True表示会过滤到空值(空列表, 空字符串, None等除了0之外的False值)
    forbidden: 必需要清除的字段
    """
    if datafrom is None:
        data = request.json or request.args.to_dict() or {}
    else:
        data = datafrom
    if filter_none:
        data = {
            k: v for k, v in data.items() if v or v == 0
        }
    if required:
        missed = list(filter(lambda x: x not in data, required))
        if missed:
            raise ParamsError('必要参数缺失或为空: ' + ', '.join(missed))
    if others != 'allow':
        data = {
            k: v for k, v in data.items() if k in required
        }
    if forbidden:
        data = {
            k: v for k, v in data.items() if k.lower() not in forbidden
        }
    return data


def validate_arg(regex, arg, msg=None):
    if arg is None:
        return
    res = re.match(regex, str(arg))
    if not res:
        raise ParamsError(msg)
    return arg
