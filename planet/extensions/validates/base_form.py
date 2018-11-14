# -*- coding: utf-8 -*-
import datetime

from flask import request
from werkzeug.datastructures import MultiDict
from wtforms import *
from wtforms.validators import *
from wtforms import StringField as _StringField
import collections

from planet.common.error_response import ParamsError


class StringField(_StringField):

    def process_formdata(self, valuelist):
        if valuelist:
            self.data = valuelist[0]
        elif self.data is None:
            return None


class BaseForm(Form):
    def __init__(self):
        if not hasattr(self, '_obj'):
            self._obj = None
        data = request.json or {}
        data = {k: v for k, v in data.items() if v or v == 0 or v is False}
        args = {k: v for k, v in request.args.to_dict().items() if v or v == 0 or v is False}
        data.update(args)
        formdata = MultiDict(_flatten_json(data))
        super(BaseForm, self).__init__(formdata)

    def valid_data(self):
        valid = super(BaseForm, self).validate()
        if not valid:
            raise ParamsError(self.errors)
        return self


# 解决 WTForms 不支持 json 形式的表单值的问题
def _flatten_json(json, parent_key='', separator='-'):
    items = []
    for key, value in json.items():
        new_key = parent_key + separator + key if parent_key else key
        if isinstance(value, collections.MutableMapping):
            items.extend(_flatten_json(value, new_key, separator).items())
        elif isinstance(value, list):
            items.extend(_flatten_json_list(value, new_key, separator))
        else:
            value = _format_value(value)
            items.append((new_key, value))
    return dict(items)


def _flatten_json_list(json, parent_key='', separator='-'):
    items = []
    i = 0
    for item in json:
        new_key = parent_key + separator + str(i)
        if isinstance(item, list):
            items.extend(_flatten_json_list(item, new_key, separator))
        elif isinstance(item, dict):
            items.extend(_flatten_json(item, new_key, separator).items())
        else:
            item = _format_value(item)
            items.append((new_key, item))
        i += 1
    return items


def _format_value(value):
    """wtforms 有些 field 只能处理字符串格式的值，无法处理 python/json 类型的值
    此函数把这些无法被处理的值转换成每种字段对应的字符串形式"""
    if value is None:
        return ''
    if isinstance(value, datetime.datetime):
        return value.isoformat().split(".").pop(0)
    if isinstance(value, int) or isinstance(value, float):
        # 若不把数字类型转换为 str ，InputValidator() 会把 0 值视为未赋值，导致验证失败
        return str(value)
    return value
