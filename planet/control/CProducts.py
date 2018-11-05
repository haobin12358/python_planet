# -*- coding: utf-8 -*-
import json
import uuid

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
        data = parameter_required(('prid',))
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
            sku.SKUattriteDetail = json.loads(sku.SKUattriteDetail)
        product.fill('skus', skus)

        # sku value
        # sku_value = self.sproduct.get_sku_value({'PRid': prid})
        # sku_value.PSKUvalue = json.loads(sku_value.PSKUvalue)
        # product.fill('sku_value', sku_value)
        product.PRattribute = json.loads(product.PRattribute)
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
            product.PRattribute = json.loads(product.PRattribute)
        return Success(data=products)

    def add_product(self):
        data = parameter_required((
            'pcid', 'pbid', 'prtitle', 'prprice',
            'prlinePrice', 'prfreight', 'prstocks',
            'prmainpic', 'prdesc', 'images'
        ))
        pbid = data.get('pbid')  # 品牌id
        pcid = data.get('pcid')  # 3级分类id
        prstatus = int(data.get('prstatus', ProductStatus.usual.value))  # 状态
        ProductStatus(prstatus)
        images = data.get('images')
        skus = data.get('skus')
        product_brand = self.sproduct.get_product_brand_one(pbid, '指定品牌不存在')
        product_category = self.sproduct.get_category_one({'PCid': pcid, 'PCtype': 3}, '指定目录不存在')
        with self.sproduct.auto_commit() as s:
            session_list = []
            # 商品
            product_dict = {
                'PRid': str(uuid.uuid4()),
                'PRtitle': data.get('prtitle'),
                'PRprice': data.get('prprice'),
                'PRlinePrice': data.get('prlinePrice'),
                'PRfreight': data.get('prfreight'),
                'PRstocks': data.get('prstocks'),
                'PRstatus': prstatus,
                'PRmainpic': data.get('prmainpic'),
                'PCid': pcid,
                'PBid': pbid,
                'PRdesc': data.get('prdesc')
            }
            product_dict = {k: v for k, v in product_dict.items()}
            product_instance = Products.create(product_dict)
            session_list.append(product_instance)
            # sku_list
            for sku in skus:
                sku_dict = {
                    'SKUid': str(uuid.uuid4()),
                    'PRid': product_dict.get('PRid'),
                    'SKUpic': sku.get('skupic'),
                    'SKUprice': sku.get('skuprice'),
                    'SKUstock': sku.get('skustock')
                }
                skudetail = data.get('skudetail')  # {kid: kid1, vid: vid2}

            # images
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
        """遍历子分类"""
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
