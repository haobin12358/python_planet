# -*- coding: utf-8 -*-
from planet.common.base_resource import Resource
from planet.control.CItems import CItems


class AItems(Resource):
    """标签"""
    def __init__(self):
        self.citems = CItems()

    def get(self, items):
        apis = {
            'list': self.citems.list,
        }
        return apis

    def post(self, items):
        apis = {
            'create': self.citems.create,
            'update': self.citems.update
        }
        return apis

