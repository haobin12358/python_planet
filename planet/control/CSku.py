# -*- coding: utf-8 -*-
import json
import uuid

from planet.common.error_response import ParamsError, NotFound
from planet.common.params_validates import parameter_required
from planet.common.success_response import Success
from planet.common.token_handler import token_required, admin_required
from planet.models import Products, ProductSku
from planet.service.SProduct import SProducts


class CSku(object):
    def __init__(self):
        self.sproduct = SProducts()

    @token_required
    def add(self):
        """添加sku"""
        data = parameter_required(('prid', 'skuattritedetail', 'skupic', 'skuprice', 'skustock'))
        prid = data.get('prid')
        # 验证
        product = self.sproduct.get_product_by_prid(prid, '商品不存在')
        skuattritedetail = data.get('skuattritedetail')
        prattribute = json.loads(product.PRattribute)
        if len(skuattritedetail) != len(prattribute) or not isinstance(skuattritedetail, list):
            raise ParamsError('skuattritedetail 参数不准确')
        price = data.get('skuprice')
        stock = data.get('skustock')
        assert price > 0 and stock > 0, '价格或库存参数不准确'
        # 添加
        with self.sproduct.auto_commit() as s:

            sku_instance = ProductSku.create({
                'SKUid': str(uuid.uuid4()),
                'PRid': prid,
                'SKUpic': data.get('skupic'),
                'SKUattriteDetail': json.dumps(skuattritedetail),
                'SKUprice': round(price, 2),
                'SKUstock': stock
            })
            s.add(sku_instance)
        return Success('添加成功', {'skuid': sku_instance.SKUid})

    @token_required
    def update(self):
        data = parameter_required(('skuid', ))
        skuid = data.get('skuid')
        price = data.get('skuprice')
        stock = data.get('skustock')
        if price:
            if price < 0:
                raise ParamsError('价格小于0')
            price = round(price, 2)
        if stock and stock < 0:
            raise ParamsError('库存小于0')
        skuattritedetail = data.get('skuattritedetail')
        with self.sproduct.auto_commit() as s:
            sku = s.query(ProductSku).filter_by_({'SKUid': skuid}).first_('sku不存在')
            product = self.sproduct.get_product_by_prid(sku.PRid)
            prattribute = json.loads(product.PRattribute)
            if len(skuattritedetail) != len(prattribute) or not isinstance(skuattritedetail, list):
                raise ParamsError('skuattritedetail 参数不准确')
            skuattritedetail = json.dumps(skuattritedetail)
            sku_dict = {
                'SKUpic': data.get('skupic'),
                'SKUprice': price,
                'SKUstock': stock,
                'SKUattriteDetail': skuattritedetail,
            }
            [setattr(sku, k, v) for k, v in sku_dict.items() if v is not None]
            s.add(sku)
        return Success('更新成功')

    @admin_required
    def delete(self):
        data = parameter_required(('skuid', ))
        skuid = data.get('skuid')
        with self.sproduct.auto_commit() as s:
            count = s.query(ProductSku).filter_by_({"SKUid": skuid}).delete_()
            if not count:
                raise NotFound('不存在的sku')
        return Success('删除成功')




