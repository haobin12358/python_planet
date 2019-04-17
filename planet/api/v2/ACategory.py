# -*- coding: utf-8 -*-
from planet.common.base_resource import Resource
from planet.control.CCategory import CCategory


class ACategory(Resource):
    def __init__(self):
        self.ccategory = CCategory()

    def get(self, category):
        apis = {
            'list': self.ccategory.get_category
        }
        return apis

    def post(self, category):
        apis = {
            'create': self.ccategory.create,
            'delete': self.ccategory.delete,
            'update': self.ccategory.update,
        }
        return apis
