# -*- coding: utf-8 -*-
from planet.common.base_resource import Resource
from planet.control.CIntegralStore import CIntegralStore


class AIntegral(Resource):
    def __init__(self):
        self.cintegral = CIntegralStore()

    def get(self, integral):
        apis = {
            'get': self.cintegral.get,
            'list': self.cintegral.list,
        }
        return apis

    def post(self, integral):
        apis = {
            'apply': self.cintegral.apply,
            'update': self.cintegral.update,
            'cancel': self.cintegral.cancel_apply,
            'delete': self.cintegral.delete,
            'shelf': self.cintegral.shelf,
            'order': self.cintegral.order,
        }
        return apis

