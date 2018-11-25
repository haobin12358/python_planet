# -*- coding: utf-8 -*-
from flask import request

from planet.common.success_response import Success
from planet.common.token_handler import token_required
from planet.extensions.register_ext import cache
from planet.extensions.validates.index import IndexListBannerForm
from planet.models import Items, ProductBrand, BrandWithItems, Products, ProductItems
from planet.service.SIndex import SIndex


class CIndex:
    def __init__(self):
        self.sindex = SIndex()

    def brand_recommend(self):
        # todo 删除首页的几个数据表
        data = {
            'brands': ProductBrand.query.join(
                BrandWithItems, BrandWithItems.PBid == ProductBrand.PBid
            ).filter_(BrandWithItems.ITid == 'index_brand').all(),
            'product': self.list_product('index_brand_product'),
            'hot': self.list_product('index_hot'),
            'recommend_for_you': self.list_product('index_recommend_product_for_you'),
        }
        return Success(data=data)

    def list_banner(self):
        form = IndexListBannerForm().valid_data()
        ibshow = dict(form.ibshow.choices).get(form.ibshow.data)
        index_banners = self.sindex.get_index_banner({'IBshow': ibshow})
        return Success(data=index_banners)

    def list_product(self, itid):
        products = Products.query.join(
            ProductItems, Products.PRid == ProductItems.PRid
        ).filter_(ProductItems.ITid == itid).all()
        for product in products:
            brand = ProductBrand.query.filter_by_({'PBid': product.PBid}).first()
            product.fields = ['PRid', 'PRtitle', 'PRprice', 'PRlinePrice', 'PRfreight', 'PRstocks', 'PRmainpic',
                              'PBid', 'PRlinePrice']
            product.fill('brand', brand)
            product.fill('pblogo', brand['PBlogo'])
        return products

    @token_required
    def set_hot(self):
        pass







