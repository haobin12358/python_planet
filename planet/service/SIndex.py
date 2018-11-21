# -*- coding: utf-8 -*-
from planet.common.base_service import SBase, close_session
from planet.config.enums import ProductBrandStatus, ProductStatus
from planet.models import IndexBrand, ProductBrand, IndexBrandProduct, Products, IndexBanner, IndexHotProduct


class SIndex(SBase):
    @close_session
    def get_index_brand(self, args=()):
        """首页推荐品牌"""
        return self.session.query(IndexBrand, ProductBrand).filter_by_(*args)\
            .join(
            ProductBrand, ProductBrand.PBid == IndexBrand.PBid
        ).filter_(
            ProductBrand.isdelete == False,
            ProductBrand.PBstatus == ProductBrandStatus.upper.value
        ).order_by(IndexBrand.IBsort).\
            all()

    @close_session
    def get_index_product(self, args=()):
        """首页推荐品牌商品"""
        return self.session.query(IndexBrandProduct, Products, ProductBrand).filter_by_(*args).join(
            Products, Products.PRid == IndexBrandProduct.PRid
        ).outerjoin(ProductBrand, Products.PBid == ProductBrand.PBid).filter(
            Products.isdelete == False,
            Products.PRstatus == ProductStatus.usual.value,
        ).order_by(IndexBrandProduct.IBPsort).all()

    @close_session
    def get_index_banner(self, args):
        """首页轮播图"""
        return self.session.query(IndexBanner).filter_by_(args).join(
            Products, IndexBanner.PRid == Products.PRid
        ).filter(Products.isdelete == False).order_by(IndexBanner.IBsort).all()

    @close_session
    def get_index_hot(self, args):
        return self.session.query(IndexHotProduct, Products, ProductBrand).filter_by_(args).join(
            Products, IndexHotProduct.PRid == Products.PRid
        ).outerjoin(ProductBrand, Products.PBid == ProductBrand.PBid).\
            filter(Products.isdelete == False).order_by(IndexHotProduct.IHPsort).all()



