# -*- coding: utf-8 -*-
from planet.common.base_resource import Resource
from planet.control.CCart import CCart


class ACart(Resource):
    def __init__(self):
        self.ccart = CCart()

    def post(self, cart):
        apis = {
            'add': self.ccart.add,
            'update': self.ccart.update,
        }
        return apis
