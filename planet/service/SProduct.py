# -*- coding: utf-8 -*-
from planet.common.base_service import SBase, close_session
from planet.models import *


class SProducts(SBase):
    @close_session
    def get_product_by_prid(self, prid, error=None):
        """获取id获取单个商品"""
        return self.session.query(Products).filter_by_(
            PRid=prid
        ).first_(error)

    @close_session
    def get_product_list(self, args, order=()):
        """获取商品列表"""
        return self.session.query(Products).filter(Products.isdelete == False).\
            outerjoin(
            ProductItems, ProductItems.PRid == Products.PRid
        ).outerjoin(
            ProductBrand, ProductBrand.PBid == Products.PBid
        ).outerjoin(Items, Items.ITid == ProductItems.ITid).\
            filter_(*args).order_by(*order).all_with_page()

    @close_session
    def get_product_images(self, args):
        """获取商品图"""
        return self.session.query(ProductImage).filter_by_(**args).\
            order_by(ProductImage.PIsort).all()

    @close_session
    def get_product_brand_one(self, args, error=None):
        """获取品牌"""
        return self.session.query(ProductBrand).filter_by_(**args).first_(error)

    @close_session
    def get_product_brand(self, args, order=()):
        """获取品牌"""
        return self.session.query(ProductBrand).filter_by_(**args).order_by(*order).all_with_page()

    @close_session
    def get_sku(self, args):
        """获取sku"""
        return self.session.query(ProductSku).filter_by_(**args).all()

    @close_session
    def get_sku_one(self, args, error=None):
        """获取单个sku"""
        return self.session.query(ProductSku).filter_by_(**args).first_(error)

    @close_session
    def get_sku_value(self, args):
        """获取sku属性值"""
        return self.session.query(ProductSkuValue).filter_by_(**args).first()

    @close_session
    def get_categorys(self, args):
        """获取分类"""
        return self.session.query(ProductCategory).filter_by_(**args).\
            order_by(ProductCategory.PCsort, ProductCategory.createtime).all()

    @close_session
    def get_category_one(self, args, error=None):
        """获取单个分类"""
        return self.session.query(ProductCategory).filter_by_(**args).first_(error)

    @close_session
    def get_item_list(self, args, order=()):
        """获取商品对应的标签"""
        return self.session.query(Items).outerjoin(ProductItems, Items.ITid == ProductItems.ITid).filter_(
            *args
        ).order_by(*order).all()

    @close_session
    def get_product_scene_one(self, args, error=None):
        """获取单个场景"""
        return self.session.query(ProductScene).filter_by_(args).first_(error)

    @close_session
    def get_product_scenes(self, kw):
        """获取所有场景"""
        return self.session.query(ProductScene).filter_(ProductScene.PSname.contains(kw),
                                                        ProductScene.isdelete == False
                                                        ).order_by(ProductScene.PSsort,
                                                                   ProductScene.createtime).all()

    @close_session
    def get_items(self, args, order=(Items.ITsort, )):
        return self.session.query(Items).outerjoin(
            SceneItem, SceneItem.ITid == Items.ITid
        ).filter_(*args).order_by(*order).all()

    @close_session
    def get_monthsale_value_one(self, args, error=None):
        return self.session.query(ProductMonthSaleValue
                                  ).filter_by_(args).order_by(ProductMonthSaleValue.createtime.desc()).first_(error)

    @close_session
    def get_search_history(self, *args, order=()):
        return self.session.query(UserSearchHistory).\
            filter_(*args).order_by(*order).group_by(
            UserSearchHistory.USHname
        ).all_with_page()

