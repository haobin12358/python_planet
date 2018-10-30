# -*- coding: utf-8 -*-
from planet.common.base_resource import Resource
from planet.control.CProducts import CCategory


class ACategory(Resource):
    def __init__(self):
        self.ccategory = CCategory()

    def get(self, category):
        apis = {
            'get_category': self.ccategory.get_category
        }
        return apis

