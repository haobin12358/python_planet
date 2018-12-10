import json
from datetime import datetime

from flask import request

from planet.common.params_validates import parameter_required
from planet.common.success_response import Success
from planet.common.token_handler import token_required
from planet.config.enums import ApplyStatus
from planet.extensions.register_ext import db
from planet.models import FreshManFirstApply, Products, FreshManFirstProduct, FreshManFirstSku, ProductSku, \
    ProductSkuValue


class CFreshManFirstOrder:
    def __init__(self):
        pass

    def list(self):
        """获取列表"""
        time_now = datetime.now()
        fresh_man_products = FreshManFirstProduct.query.join(
            FreshManFirstApply, FreshManFirstApply.FMFAid == FreshManFirstProduct.FMFAid
        ).filter_(
            FreshManFirstApply.FMFAstatus == ApplyStatus.agree.value,
            FreshManFirstApply.AgreeStartime <= time_now,
            FreshManFirstApply.AgreeEndtime >= time_now,
            FreshManFirstApply.isdelete == False,
            FreshManFirstProduct.isdelete == False,
        ).all()
        for fresh_man_product in fresh_man_products:
            fresh_man_product.hide('PRattribute', 'PRid', 'PBid', )
        return Success(data=fresh_man_products)

    def get(self):
        """获取单个新人商品"""
        data = parameter_required(('fmfpid', ))
        fmfpid = data.get('fmfpid')
        fresh_man_first_product = FreshManFirstProduct.query.filter_by_({
            'FMFPid': fmfpid
        }).first_('商品不存在')
        #
        prid = fresh_man_first_product.PRid
        product = Products.query.filter_by_({'PRid': prid}).first_('商品不存在')
        product.PRprice = fresh_man_first_product.PRprice
        product.PRfeight = fresh_man_first_product.PRfeight
        product.PRattribute = json.loads(product.PRattribute)
        product.PRtitle = fresh_man_first_product.PRtitle
        # 新人商品sku
        fresh_man_skus = FreshManFirstSku.query.filter_by_({'FMFPid': fmfpid}).all()

        product_skus = []  # sku对象
        sku_value_item = []
        for fresh_man_sku in fresh_man_skus:
            product_sku = ProductSku.query.filter_by_({'SKUid': fresh_man_sku.SKUid}).first()
            product_sku.SKUprice = fresh_man_sku.SKUprice
            product_skus.append(product_sku)
            product_sku.SKUattriteDetail = json.loads(product_sku.SKUattriteDetail)
            sku_value_item.append(product_sku.SKUattriteDetail)  # 原商品的sku
        product.fill('skus', product_skus)

        # 是否有skuvalue, 如果没有则自行组装(这个sku_value是商品的sku_value, 而不再单独设置新人商品的sku)
        sku_value_instance = ProductSkuValue.query.filter_by_({
            'PRid': prid
        }).first()
        if not sku_value_instance:
            sku_value_item_reverse = []
            for index, name in enumerate(product.PRattribute):
                value = list(set([attribute[index] for attribute in sku_value_item]))
                value = sorted(value)
                temp = {
                    'name': name,
                    'value': value
                }
                sku_value_item_reverse.append(temp)
        else:
            sku_value_item_reverse = []  # 转置
            pskuvalue = json.loads(sku_value_instance.PSKUvalue)
            for index, value in enumerate(pskuvalue):
                sku_value_item_reverse.append({
                    'name': product.PRattribute[index],
                    'value': value
                })
        product.fill('SkuValue', sku_value_item_reverse)
        return Success(product)

    @token_required
    def add_order(self):
        """购买, 返回支付参数"""
        data = parameter_required(('skuid', 'omclient', 'uaid', 'opaytype'))
        # 只可以买一次
        usid = request.user.id
        exists_order = OrderMain.query.filter_(
            OrderMain.USid == usid, OrderMain.OMstatus > OrderMainStatus.wait_pay.value
        ).first()
        if exists_order:
            raise StatusError()
        # 判断是否是别人分享而来



