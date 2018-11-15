# -*- coding: utf-8 -*-
from planet.common.base_resource import Resource
from planet.control.CRefund import CRefund


class ARefund(Resource):
    """退款"""
    def __init__(self):
        self.crefund = CRefund()

    def post(self, refund):
        apis = {
            'create': self.crefund.create
        }
        return apis
