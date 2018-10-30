# -*- coding: utf-8 -*-
from planet.common.base_resource import Resource
from planet.control.CProducts import CProducts


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
        apis ={
            'add_product': self.cproduct.add_product,
        }
        return apis
