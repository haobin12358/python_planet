# -*- coding: utf-8 -*-
from wtforms.validators import *
from wtforms import *

from planet.config.enums import OrderMainStatus
from planet.models.trade import OrderMain
from .base_form import BaseForm


class OrderSendForm(BaseForm):
    """发货"""
    omid = StringField('主单id', validators=[DataRequired()])
    olcompany = StringField('物流公司', validators=[DataRequired()])
    olexpressno = StringField('单号', validators=[DataRequired()])

    def validate_olcompany(self, raw):
        pass


class OrderListForm(BaseForm):
    omstatus = Field()

    def validate_omstatus(self, raw):
        try:
            if raw.data is None:
                self.omstatus.data = []
            else:
                raw.data = int(raw.data)
                OrderMainStatus(raw.data)
                self.omstatus.data = [
                    OrderMain.OMstatus == raw.data,
                    OrderMain.OMinRefund == False
                ]
        except ValueError as e:
            if raw.data == 'inrefund':
                self.omstatus.data = [
                    OrderMain.OMinRefund == True,
                ]
            else:
                raise ValidationError('status 参数错误')
        except Exception as e:
            raise e
