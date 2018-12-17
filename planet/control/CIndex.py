# -*- coding: utf-8 -*-
from flask import request, current_app

from planet.common.success_response import Success
from planet.common.token_handler import token_required, admin_required
from planet.extensions.register_ext import cache, db
from planet.extensions.validates.index import IndexListBannerForm, IndexSetBannerForm
from planet.models import Items, ProductBrand, BrandWithItems, Products, ProductItems
from planet.service.SIndex import SIndex


class CIndex:
    def __init__(self):
        self.sindex = SIndex()

    @cache.cached(timeout=30, key_prefix='index')
    def brand_recommend(self):
        current_app.logger.info('获取首页信息')
        data = {
            'brands': ProductBrand.query.join(
                BrandWithItems, BrandWithItems.PBid == ProductBrand.PBid
            ).filter_(BrandWithItems.ITid == 'index_brand',
                      ProductBrand.isdelete == False).all(),
            'product': self.list_product('index_brand_product'),
            'hot': self.list_product('index_hot'),
            'recommend_for_you': self.list_product('index_recommend_product_for_you'),
        }
        return Success(data=data)

    @cache.cached(timeout=30, key_prefix='index_banner')
    def list_banner(self):
        form = IndexListBannerForm().valid_data()
        ibshow = dict(form.ibshow.choices).get(form.ibshow.data)
        index_banners = self.sindex.get_index_banner({'IBshow': ibshow})
        return Success(data=index_banners)

    @admin_required
    def set_banner(self):
        form = IndexSetBannerForm().valid_data()
        with db.auto_commit():
            # todo 设置主页显示信息
            product = Products.query.filter(
                Products.isdelete == False,
                # Produ
            )

    def list_product(self, itid):
        products = Products.query.join(
            ProductItems, Products.PRid == ProductItems.PRid
        ).filter_(ProductItems.ITid == itid,
                  Products.isdelete == False,
                  ProductItems.isdelete == False
                  ).all()
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







