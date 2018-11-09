# -*- coding: utf-8 -*-
from planet.common.base_resource import Resource
from planet.control.CUser import CUser


class AAddress(Resource):
    def __init__(self):
        self.user = CUser()

    def get(self, address):
        apis = {
            'get_provinces': self.user.get_all_province,
            'get_citys': self.user.get_citys_by_provinceid,
            'get_areas': self.user.get_areas_by_cityid,
        }
        return apis
