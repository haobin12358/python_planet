# -*- coding: utf-8 -*-
from planet.common.base_resource import Resource
from planet.control.CTrialCommodity import CTrialCommodity


class ATrialCommodity(Resource):
    def __init__(self):
        self.ctrialcommodity = CTrialCommodity()

    def get(self, commodity):
        apis = {
            'get': self.ctrialcommodity.get_commodity_list,
            'get_commodity': self.ctrialcommodity.get_commodity,
        }
        return apis

    def post(self, commodity):
        apis = {
            'add': self.ctrialcommodity.add_commodity,
            'create_order': self.ctrialcommodity.create_order,
            'update': self.ctrialcommodity.update_commodity,
            'del': self.ctrialcommodity.del_commodity,
        }
        return apis