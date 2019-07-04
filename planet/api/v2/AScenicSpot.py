# -*- coding: utf-8 -*-
from planet.common.base_resource import Resource
from planet.control.CScenicSpot import CScenicSpot


class AScenicSpot(Resource):
    """景区"""
    def __init__(self):
        self.cscenicspot = CScenicSpot()

    def get(self, scenicspot):
        apis = {
            'get': self.cscenicspot.get,
            'list': self.cscenicspot.list,
        }
        return apis

    def post(self, scenicspot):
        apis = {
            'add': self.cscenicspot.add,
            'update': self.cscenicspot.update,
            'delete': self.cscenicspot.delete,
        }
        return apis
