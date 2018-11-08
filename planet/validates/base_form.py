# -*- coding: utf-8 -*-
from flask import request
from wtforms import Form

from ..common.error_response import ParamsError


class BaseForm(Form):
    def __init__(self):
        data = request.json
        args = request.args.to_dict()
        super(BaseForm, self).__init__(data=data, **args)

    def validate_for_api(self):
        valid = super(BaseForm, self).validate()
        if not valid:
            raise ParamsError(self.errors)
        return self
