# -*- coding: utf-8 -*-
from flask import request
from wtforms.validators import *
from wtforms import *

from planet.common.error_response import AuthorityError
from planet.common.token_handler import is_admin
from planet.config.enums import OrderMainStatus
from planet.models.trade import OrderMain
from .base_form import BaseForm


class OrderListForm(BaseForm):
    omstatus = Field('状态')
    issaler = BooleanField('卖家版', default=False)
    usid = StringField('用户id')

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

    def validate_usid(self, raw):
        if not is_admin() and self.issaler.data is False:  # 买家版仅可以查看自己的订单
            if raw.data != request.user.id:
                raise AuthorityError()
            usid = request.user.id
        elif not is_admin() and self.issaler.data is True:  # 卖家不筛选usid
            usid = None
        else:
            usid = raw.data  # 管理员可以任意筛选usid
        self.usid.data = usid

    def validate_issaler(self, raw):
        """是否卖家"""
        if raw.data is True:
            pass



