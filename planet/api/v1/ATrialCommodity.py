# -*- coding: utf-8 -*-
from planet.common.base_resource import Resource
from planet.control.CTrialCommodity import CTrialCommodity


class ATrialCommodity(Resource):
    def __init__(self):
        self.ctrialcommodity = CTrialCommodity()

    def get(self, commodity):
        apis = {
            'get': self.ctrialcommodity.get_commodity_list,
        }
        return apis