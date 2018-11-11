# -*- coding: utf-8 -*-
from flask import request
from wtforms import Form

from planet.common.error_response import ParamsError


class BaseForm(Form):
    def __init__(self):
        data = request.json or {}
        data = {k: v for k, v in data.items() if v or v == 0}
        args = {k: v for k, v in request.args.to_dict().items() if v or v == 0}
        super(BaseForm, self).__init__(data=data, **args)

    def valid_data(self):
        valid = super(BaseForm, self).validate()
        if not valid:
            raise ParamsError(self.errors)
        return self
