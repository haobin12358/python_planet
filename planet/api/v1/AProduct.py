# -*- coding: utf-8 -*-
from planet.control.CProducts import CProducts
from planet.common.base_resource import Resource


class AProduct(Resource):
    def __init__(self):
        self.cproduct = CProducts()

    def get(self, product):
        apis = {
            'get': self.cproduct.get_product,
            'list': self.cproduct.get_produt_list,
            'guess_search': self.cproduct.guess_search,
            'search_history': self.cproduct.search_history,  # 搜索记录
        }
        return apis

    def post(self, product):
        apis = {
            'create': self.cproduct.add_product,
            'update': self.cproduct.update_product,
            'delete': self.cproduct.delete,
            'delete_list': self.cproduct.delete_list,
            'off_shelves': self.cproduct.off_shelves,  # 上下架
            'off_shelves_list': self.cproduct.off_shelves_list,
            'del_search_history': self.cproduct.del_search_history,
            'agree_product': self.cproduct.agree_product,  # 同意审批
            'resubmit_product': self.cproduct.resubmit_product,  # 重新提交审核
        }
        return apis





