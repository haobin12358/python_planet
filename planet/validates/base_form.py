# -*- coding: utf-8 -*-
from flask import request
from wtforms import Form

from ..common.error_response import ParamsError


class BaseForm(Form):
    def __init__(self, formdata=None, obj=None, prefix='', data=None, meta=None, **kwargs):
        if formdata is not None or obj is not None or prefix or data is not None or meta is not None or kwargs:
            super(BaseForm, self).__init__(formdata=None, obj=None, prefix='', data=None, meta=None, **kwargs)
        else:
            data = request.json
            args = request.args.to_dict()
            super(BaseForm, self).__init__(data=data, **args)

    def valid_data(self):
        valid = super(BaseForm, self).validate()
        if not valid:
            raise ParamsError(self.errors)
        return self
