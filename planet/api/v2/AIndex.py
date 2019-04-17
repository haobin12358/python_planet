# -*- coding: utf-8 -*-
from planet.common.base_resource import Resource
from planet.control.CIndex import CIndex


class AIndex(Resource):
    def __init__(self):
        self.cindex = CIndex()

    def get(self, index):
        apis = {
            # 'list_brand': self.cindex.list_brand,
            'list_banner': self.cindex.list_banner,
            'list_product': self.cindex.list_product,
            'brand_recommend': self.cindex.brand_recommend,
        }
        return apis

    def post(self, index):
        apis = {
            'set_banner': self.cindex.set_banner,
            'update_banner': self.cindex.update_banner,
        }
        return apis

