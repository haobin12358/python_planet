# -*- coding: utf-8 -*-
import uuid

from flask import request, current_app

from planet.common.error_response import SystemError
from planet.common.success_response import Success
from planet.common.token_handler import token_required, admin_required
from planet.config.enums import ProductStatus
from planet.extensions.register_ext import cache, db
from planet.extensions.validates.index import IndexListBannerForm, IndexSetBannerForm, IndexUpdateBannerForm
from planet.models import Items, ProductBrand, BrandWithItems, Products, ProductItems, IndexBanner
from planet.service.SIndex import SIndex


class CIndex:
    def __init__(self):
        self.sindex = SIndex()

    # @cache.cached(timeout=30, key_prefix='index')
    def brand_recommend(self):
        current_app.logger.info('获取首页信息')
        data = {
            'brands': ProductBrand.query.join(
                BrandWithItems, BrandWithItems.PBid == ProductBrand.PBid
            ).filter(BrandWithItems.ITid == 'index_brand',
                      ProductBrand.isdelete == False,
                     BrandWithItems.isdelete == False).all(),
            'product': self.list_product('index_brand_product'),
            'hot': self.list_product('index_hot'),
            'recommend_for_you': self.list_product('index_recommend_product_for_you'),
        }
        return Success(data=data)

    # @cache.cached(timeout=30, key_prefix='index_banner')
    def list_banner(self):
        form = IndexListBannerForm().valid_data()
        ibshow = dict(form.ibshow.choices).get(form.ibshow.data)
        index_banners = self.sindex.get_index_banner({'IBshow': ibshow})
        # [index_banner.fill('prtitle', Products.query.filter_by_(PRid=index_banner.PRid).first()['PRtitle'])
        #  for index_banner in index_banners]
        return Success(data=index_banners)

    @admin_required
    def set_banner(self):
        current_app.logger.info("Admin {} set index banner".format(request.user.username))
        form = IndexSetBannerForm().valid_data()
        ibid = str(uuid.uuid1())
        with db.auto_commit():
            banner = IndexBanner.create({
                'IBid': ibid,
                'contentlink': form.contentlink.data,
                'IBpic': form.ibpic.data,
                'IBsort': form.ibsort.data,
                'IBshow': form.ibshow.data
            })
            db.session.add(banner)
        return Success('添加成功', {'ibid': ibid})

    @admin_required
    def update_banner(self):
        current_app.logger.info("Admin {} update index banner".format(request.user.username))
        form = IndexUpdateBannerForm().valid_data()
        ibid= form.ibid.data
        isdelete = form.isdelete.data
        IndexBanner.query.filter_by_(IBid=ibid).first_('未找到该轮播图信息')
        with db.auto_commit():
            banner_dict = {'IBid': ibid,
                           'contentlink': form.contentlink.data,
                           'IBpic': form.ibpic.data,
                           'IBsort': form.ibsort.data,
                           'IBshow': form.ibshow.data,
                           'isdelete': isdelete
                           }
            banner_dict = {k: v for k, v in banner_dict.items() if v is not None}
            banner = IndexBanner.query.filter_by_(IBid=ibid).update(banner_dict)
            if not banner:
                raise SystemError('服务器繁忙 10000')
        return Success('修改成功', {'ibid': ibid})

    def list_product(self, itid):
        products = Products.query.join(
            ProductItems, Products.PRid == ProductItems.PRid
        ).filter_(ProductItems.ITid == itid,
                  Products.isdelete == False,
                  ProductItems.isdelete == False,
                  ProductBrand.PBid == Products.PBid,
                  ProductBrand.isdelete == False,
                  Products.PRstatus == ProductStatus.usual.value
                  ).all()
        for product in products:
            brand = ProductBrand.query.filter_by_({'PBid': product.PBid}).first()
            if not brand:
                continue
            product.fields = ['PRid', 'PRtitle', 'PRprice', 'PRlinePrice', 'PRfreight', 'PRstocks', 'PRmainpic',
                              'PBid', 'PRlinePrice']
            product.fill('brand', brand)
            product.fill('pblogo', brand['PBlogo'])
        return products

    @token_required
    def set_hot(self):
        pass







