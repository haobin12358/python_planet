# -*- coding: utf-8 -*-
from planet.control.CProducts import CProducts, CCategory
from planet.common.base_resource import Resource


class AProduct(Resource):
    def __init__(self):
        self.cproduct = CProducts()

    def get(self, product):
        apis = {
            'get_product': self.cproduct.get_product,
            'get_product_list': self.cproduct.get_produt_list,
        }
        return apis

    def post(self, product):
        apis = {
            'add_product': self.cproduct.add_product,
        }
        return apis


class ACategory(Resource):
    def __init__(self):
        self.ccategory = CCategory()

    def get(self, category):
        apis = {
            'get_category': self.ccategory.get_category
        }
        return apis
