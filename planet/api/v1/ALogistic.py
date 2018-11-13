# -*- coding: utf-8 -*-
from planet.common.base_resource import Resource
from planet.control.CLogistic import CLogistic


class ALogistic(Resource):
    def __init__(self):
        self.clogistic = CLogistic()

    def get(self, logistic):
        apis = {
            'list_company': self.clogistic.list_company
        }
        return apis
