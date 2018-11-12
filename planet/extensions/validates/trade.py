# -*- coding: utf-8 -*-
from wtforms.validators import *
from wtforms import *

from .base_form import BaseForm


class OrderSendForm(BaseForm):
    """发货"""
    omid = StringField('主单id', validators=[DataRequired()])
    olcompany = StringField('物流公司', validators=[DataRequired()])
    olexpressno = StringField('单号', validators=[DataRequired()])

    def validate_olcompany(self, raw):
        pass
