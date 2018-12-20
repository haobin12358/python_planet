# -*- coding: utf-8 -*-
from planet.common.base_resource import Resource
from planet.control.CRefund import CRefund


class ARefund(Resource):
    """退款"""
    def __init__(self):
        self.crefund = CRefund()

    def post(self, refund):
        apis = {
            'create': self.crefund.create,
            'create_dispute_type': self.crefund.create_dispute_type,
            'agree_apply': self.crefund.agree_apply,  # 同意售后申请
            'send': self.crefund.send,
            'cancle': self.crefund.cancle,
            'back_confirm_recv': self.crefund.back_confirm_recv,
            'back_confirm_refund': self.crefund.back_confirm_refund,
        }
        return apis

    def get(self, refund):
        apis = {
            'list_dispute_type': self.crefund.list_dispute_type,
        }
        return apis
