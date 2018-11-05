# -*- coding: utf-8 -*-
from planet.control.CProducts import CProducts, CCategory
from planet.common.base_resource import Resource


class AProduct(Resource):
    def __init__(self):
        self.cproduct = CProducts()

    def get(self, product):
        apis = {
            'get': self.cproduct.get_product,
            'list': self.cproduct.get_produt_list,
        }
        return apis

    def post(self, product):
        apis = {
            'create': self.cproduct.add_product,
        }
        return apis


class ACategory(Resource):
    def __init__(self):
        self.ccategory = CCategory()

    def get(self, category):
        apis = {
            'list': self.ccategory.get_category
        }
        return apis
