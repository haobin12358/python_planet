# -*- coding: utf-8 -*-
from planet.common.base_resource import Resource
from planet.control.CBrands import CBrands


class ABrands(Resource):
    def __init__(self):
        self.cbrands = CBrands()

    def post(self, brand):
        apis = {
            'create': self.cbrands.create,
            'off_shelves': self.cbrands.off_shelves,
            'update': self.cbrands.update,
            'set_banner': self.cbrands.set_banner,
            'delete': self.cbrands.delete
        }
        return apis

    def get(self, brand):
        apis = {
            'list': self.cbrands.list,
            'get_recommend_product': self.cbrands.get_recommend_product,
            'get_banner': self.cbrands.get_banner,
            'list_with_group': self.cbrands.list_with_group,
            'get': self.cbrands.get,
        }
        return apis
