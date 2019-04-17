# -*- coding: utf-8 -*-
from planet.common.base_resource import Resource
from planet.control.CCart import CCart


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

