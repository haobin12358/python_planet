# -*- coding: utf-8 -*-
from planet.common.base_resource import Resource
from planet.control.CIndex import CIndex


class AIndex(Resource):
    def __init__(self):
        self.cindex = CIndex()

    def get(self, index):
        apis = {
            'list_brand': self.cindex.list_brand,
            'list_banner': self.cindex.list_banner,
            'list_product': self.cindex.list_product
        }
        return apis

