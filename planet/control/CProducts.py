# -*- coding: utf-8 -*-
import json
import uuid

from flask import request
from sqlalchemy import or_

from planet.common.error_response import NotFound, ParamsError, AuthorityError
from planet.common.params_validates import parameter_required
from planet.common.success_response import Success
from planet.common.token_handler import token_required, is_admin, is_shop_keeper
from planet.config.enums import ProductStatus, ProductFrom
from planet.models import Products, ProductBrand, ProductItems, ProductSku, ProductImage, Items
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
        product.PRattribute = json.loads(product.PRattribute)
        product.PRremarks = json.loads(getattr(product, 'PRremarks') or '{}')
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
        # 场景
        items = self.sproduct.get_item_list([
            ProductItems.PRid == prid
        ])
        product.fill('items', items)
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
            product.PRremarks = json.loads(getattr(product, 'PRremarks') or '{}')
        return Success(data=products)

    @token_required
    def add_product(self):
        self._can_add_product()
        data = parameter_required((
            'pcid', 'pbid', 'prtitle', 'prprice', 'prattribute',
            'prstocks', 'prmainpic', 'prdesc', 'images', 'skus'
        ))
        pbid = data.get('pbid')  # 品牌id
        pcid = data.get('pcid')  # 3级分类id
        images = data.get('images')
        skus = data.get('skus')
        product_brand = self.sproduct.get_product_brand_one({'PBid': pbid}, '指定品牌不存在')
        product_category = self.sproduct.get_category_one({'PCid': pcid, 'PCtype': 3}, '指定目录不存在')
        # 商品来源
        with self.sproduct.auto_commit() as s:
            session_list = []
            # 商品
            prattribute = data.get('prattribute')
            prid = str(uuid.uuid4())
            prmarks = data.get('prmarks')  # 备注
            if prmarks:
                try:
                    prmarks = json.dumps(prmarks)
                    if not isinstance(prmarks, dict):
                        raise TypeError
                except Exception as e:
                    pass
            product_dict = {
                'PRid': prid,
                'PRtitle': data.get('prtitle'),
                'PRprice': data.get('prprice'),
                'PRlinePrice': data.get('prlinePrice'),
                'PRfreight': data.get('prfreight'),
                'PRstocks': data.get('prstocks'),
                'PRmainpic': data.get('prmainpic'),
                'PCid': pcid,
                'PBid': pbid,
                'PRdesc': data.get('prdesc'),
                'PRattribute': json.dumps(prattribute),
                'PRremarks': prmarks,
                'PRfrom': self.product_from,
                'CreaterId': request.user.id,
                'PRstatus': self.prstatus,

            }
            product_dict = {k: v for k, v in product_dict.items()}
            product_instance = Products.create(product_dict)
            session_list.append(product_instance)
            # sku
            for sku in skus:
                skuattritedetail = sku.get('skuattritedetail')
                if not isinstance(skuattritedetail, list) or len(skuattritedetail) != len(skuattritedetail):
                    raise ParamsError('skuattritedetail与prattribute不符')
                sku_dict = {
                    'SKUid': str(uuid.uuid4()),
                    'PRid': prid,
                    'SKUpic': sku.get('skupic'),
                    'SKUprice': sku.get('skuprice'),
                    'SKUstock': sku.get('skustock'),
                    'SKUattriteDetail': json.dumps(skuattritedetail)
                }
                sku_instance = ProductSku.create(sku_dict)
                session_list.append(sku_instance)
            # images
            for image in images:
                image_dict = {
                    'PIid': str(uuid.uuid4()),
                    'PRid': prid,
                    'PIpic': image.get('pipic'),
                    'PIsort': image.get('pisort'),
                }
                image_instance = ProductImage.create(image_dict)
                session_list.append(image_instance)
            # 场景下的小标签 [{'itid': itid1}, ...]
            items = data.get('items')
            if items:
                for item in items:
                    itid = item.get('itid')
                    item = s.query(Items).filter_by_({'ITid': itid}).first_('指定标签不存在')
                    item_product_dict = {
                        'PIid': str(uuid.uuid4()),
                        'PRid': prid,
                        'ITid': itid
                    }
                    item_product_instance = ProductItems.create(item_product_dict)
                    session_list.append(item_product_instance)
            s.add_all(session_list)
        return Success('添加成功', {'prid': prid})

    def _can_add_product(self):
        if is_admin():
            self.product_from = ProductFrom.platform.value
            self.prstatus = None
        elif is_shop_keeper():
            self.product_from = ProductFrom.shop_keeper.value
            self.prstatus = ProductStatus.auditing.value
        else:
            raise AuthorityError()
