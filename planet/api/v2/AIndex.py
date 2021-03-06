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
            'list_hypermarket_banner': self.cindex.list_hypermarket_banner,
            'get_entry': self.cindex.get_entry,
            'list_linkcontent': self.cindex.list_linkcontent,
            'get_linkcontent': self.cindex.get_linkcontent,
            'list_mp_banner': self.cindex.list_mp_banner

        }
        return apis

    def post(self, index):
        apis = {
            'set_banner': self.cindex.set_banner,
            'update_banner': self.cindex.update_banner,
            'set_hypermarket_banner': self.cindex.set_hypermarket_banner,
            'set_entry': self.cindex.set_entry,
            'set_linkcontent': self.cindex.set_linkcontent,
            'set_mp_banner': self.cindex.set_mp_banner
        }
        return apis

