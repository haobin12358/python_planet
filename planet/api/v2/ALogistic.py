# -*- coding: utf-8 -*-
from planet.common.base_resource import Resource
from planet.control.CLogistic import CLogistic


class ALogistic(Resource):
    """物流相关"""
    def __init__(self):
        self.clogistic = CLogistic()

    def get(self, logistic):
        apis = {
            'list_company': self.clogistic.list_company,
            'get': self.clogistic.get,
        }
        return apis

    def post(self, logistic):
        apis = {
            'subcribe_callback': self.clogistic.subcribe_callback,
            'send': self.clogistic.send,
        }
        return apis
