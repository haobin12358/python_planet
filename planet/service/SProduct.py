# -*- coding: utf-8 -*-
from planet.common.base_service import SBase, close_session
from planet.models import Products, ProductCategory, ProductImage, ProductBrand, ProductSkuValue, ProductSku, \
    ProductItems


class SProducts(SBase):
    @close_session
    def get_product_by_prid(self, prid):
        """获取id获取单个商品"""
        return self.session.query(Products).filter_by_(
            PRid=prid
        ).first()

    @close_session
    def get_product_list(self, args, order=[]):
        """获取商品列表"""
        return self.session.query(Products).filter_by_().\
            outerjoin(
                ProductItems, ProductItems.PRid == Products.PRid
            ).filter_(*args).order_by(*order).all_with_page()

    @close_session
    def get_product_images(self, args):
        """获取商品图"""
        return self.session.query(ProductImage).filter_by_(**args).\
            order_by(ProductImage.PIsort).all()

    @close_session
    def get_product_brand_one(self, args):
        """获取品牌"""
        return self.session.query(ProductBrand).filter_by_(**args).first()

    @close_session
    def get_sku(self, args):
        """获取sku"""
        return self.session.query(ProductSku).filter_by_(**args).all()

    @close_session
    def get_sku_one(self, args):
        """获取单个sku"""
        return self.session.query(ProductSku).filter_by_(**args).first()

    @close_session
    def get_sku_value(self, args):
        """获取sku属性值"""
        return self.session.query(ProductSkuValue).filter_by_(**args).first()

    @close_session
    def get_categorys(self, args):
        """获取分类"""
        return self.session.query(ProductCategory).filter_by_(**args).\
            order_by(ProductCategory.PCsort).all()
