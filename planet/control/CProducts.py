# -*- coding: utf-8 -*-
import json

from sqlalchemy import or_

from planet.common.error_response import NotFound, ParamsError
from planet.common.params_validates import parameter_required
from planet.common.success_response import Success
from planet.config.enums import ProductStatus
from planet.models import Products, ProductBrand, ProductItems
from planet.service.SProduct import SProducts


class CProducts:
    def __init__(self):
        self.sproduct = SProducts()

    def get_product(self):
        data = parameter_required(('prid', ))
        prid = data.get('prid')
        product = self.sproduct.get_product_by_prid(prid)
        if not product:
            return NotFound()
        product.fill('prstatus_en', ProductStatus(product.PRstatus).name)
        # 顶部图
        images = self.sproduct.get_product_images({'PRid': prid})
        product.fill('images', images)
        # 品牌
        brand = self.sproduct.get_product_brand_one({'PBid': product.PBid}) or {}
        product.fill('brand', brand)
        # sku
        skus = self.sproduct.get_sku({'PRid': prid})
        for sku in skus:
            sku.SKUdetail = json.loads(sku.SKUdetail)
        product.fill('skus', skus)
        # sku value
        sku_value = self.sproduct.get_sku_value({'PRid': prid})
        sku_value.PSKUvalue = json.loads(sku_value.PSKUvalue)
        product.fill('sku_value', sku_value)
        return Success(data=product)

    def get_produt_list(self):
        data = parameter_required()
        order = data.get('order', 'desc')  # 时间排序
        kw = data.get('kw', '')  # 关键词
        pbid = data.get('pbid')  # 品牌
        pcid = data.get('pcid')  # 分类id
        itid = data.get('itid')  # 场景下的标签id

        if order == 'desc':
            order = Products.createtime.desc()
        else:
            order = Products.createtime
        # 筛选
        products = self.sproduct.get_product_list([
            Products.PBid == pbid,
            or_(Products.PRtitle.contains(kw), ProductBrand.PBname.contains(kw)),
            Products.PCid == pcid,
            ProductItems.ITid == itid
        ], [order, ])
        # 填充
        for product in products:
            product.fill('prstatus_en', ProductStatus(product.PRstatus).name)
            # 品牌
            brand = self.sproduct.get_product_brand_one({'PBid': product.PBid})
            product.fill('brand', brand)
        return Success(data=products)

    def add_product(self):
        pass


class CCategory(object):
    def __init__(self):
        self.sproduct = SProducts()

    def get_category(self):
        """获取类目"""
        data = parameter_required()
        up = data.get('up', '')
        deep = data.get('deep', 0)  # 深度
        categorys = self.sproduct.get_categorys({'ParentPCid': up})
        for category in categorys:
            self._sub_category(category, deep)
        return Success(data=categorys)

    def _sub_category(self, category, deep):
        try:
            deep = int(deep)
        except TypeError as e:
            raise ParamsError()
        print('hello')
        if deep <= 0:
            return
        deep -= 1
        subs = self.sproduct.get_categorys({'ParentPCid': category.PCid})
        if subs:
            category.fill('subs', subs)
            for sub in subs:
                self._sub_category(sub, deep)

