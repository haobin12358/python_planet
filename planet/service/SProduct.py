# -*- coding: utf-8 -*-
from planet.common.base_service import SBase, close_session
from planet.models import Products, ProductCategory


class SProducts(SBase):
    @close_session
    def get_product_by_prid(self, prid):
        return self.session.query(Products).filter_by_(
            PRid=prid
        ).first()

    @close_session
    def get_categorys(self, args):
        """获取分类"""
        return self.session.query(ProductCategory).filter_by_(**args).\
            order_by(ProductCategory.PCsort).all()
