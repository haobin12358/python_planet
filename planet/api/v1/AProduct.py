# -*- coding: utf-8 -*-
from planet.control.CCategory import CCategory
from planet.control.CProducts import CProducts
from planet.common.base_resource import Resource
from planet.control.CScene import CScene
from planet.control.CSku import CSku
from planet.control.CBrands import CBrands


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
            'off_shelves': self.cproduct.off_shelves,  # 上下架
            'del_search_history': self.cproduct.del_search_history,
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

    def post(self, category):
        apis = {
            'create': self.ccategory.create,
            'delete': self.ccategory.delete,
        }
        return apis


class ASku(Resource):
    def __init__(self):
        self.csku = CSku()

    def post(self, sku):
        apis = {
            'create': self.csku.add,
            'update': self.csku.update,
        }
        return apis


class ABrands(Resource):
    def __init__(self):
        self.cbrands = CBrands()

    def post(self, brand):
        apis = {
            'create': self.cbrands.create,
            'off_shelves': self.cbrands.off_shelves,
            'update': self.cbrands.update,
        }
        return apis

    def get(self, brand):
        apis = {
            'list': self.cbrands.list,
        }
        return apis


class AScene(Resource):
    """场景"""
    def __init__(self):
        self.cscene = CScene()

    def get(self, scene):
        apis = {
            'list': self.cscene.list
        }
        return apis

    def post(self, scene):
        apis = {
            'create': self.cscene.create
        }
        return apis
