# -*- coding: utf-8 -*-
from planet.common.base_resource import Resource
from planet.control.CCart import CCart
from planet.control.COrder import COrder
from planet.control.CRefund import CRefund


class ACart(Resource):
    def __init__(self):
        self.ccart = CCart()

    def post(self, cart):
        apis = {
            'create': self.ccart.add,
            'update': self.ccart.update,
            'destroy': self.ccart.destroy,
        }
        return apis

    def get(self, cart):
        apis = {
            'list': self.ccart.list,
        }
        return apis


class AOrder(Resource):
    def __init__(self):
        self.corder = COrder()

    def post(self, order):
        apis = {
            'create': self.corder.create,
            'pay': self.corder.pay,
            'alipay_notify': self.corder.alipay_notify,
            'wechat_notify': self.corder.wechat_notify,
        }
        return apis

    def get(self, order):
        apis = {
            'list': self.corder.list,
            'get': self.corder.get,
        }
        return apis


class ARefund(Resource):
    """退款"""
    def __init__(self):
        self.crefund = CRefund()

    def post(self, refund):
        apis = {
            'create': self.crefund.create
        }
        return apis
