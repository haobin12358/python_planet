# -*- coding: utf-8 -*-
from .base_form import *


class OrderSendForm(BaseForm):
    """发货"""
    omid = StringField('主单id', validators=[DataRequired('请指定订单')])
    olcompany = StringField('物流公司', validators=[DataRequired('物流公司不可为空')])
    olexpressno = StringField('单号', validators=[DataRequired('单号不可为空')])

    def validate_olcompany(self, raw):
        pass

