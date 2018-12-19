# -*- coding: utf-8 -*-
import uuid

from flask import request, json

from planet.common.error_response import ParamsError
from planet.common.params_validates import parameter_required
from planet.common.success_response import Success
from planet.common.token_handler import token_required
from planet.config.enums import ProductStatus
from planet.models import ProductSku, Products
from planet.models.trade import Carts
from planet.service.SProduct import SProducts
from planet.service.STrade import STrade


class CCart(object):
    def __init__(self):
        self.scart = STrade()
        self.sproduct = SProducts()

    @token_required
    def add(self):
        """添加购物车"""
        data = parameter_required(('skuid', ))
        skuid = data.get('skuid')
        try:
            num = int(data.get('canums', 1))
        except TypeError as e:
            raise ParamsError('num参数类型错误')
        usid = request.user.id
        is_exists = self.scart.get_card_one({'USid': usid, 'SKUid': skuid})
        if is_exists:
            # 已存在
            caid = is_exists.CAid
            with self.scart.auto_commit() as session:
                new_nums = is_exists.CAnums
                if new_nums <= 0:
                    # 数目过小则为删除
                    session.query(Carts).filter_by_({'CAid': caid}).update({
                        'isdelete': True
                    })
                    msg = '删除购物车成功'
                else:
                    # 更新数据
                    session.query(Carts).filter_by_({'CAid': caid}).update({
                        'CAnums': Carts.CAnums + num
                    })
                    msg = '更新购物车成功'
        else:
            # 不存在
            with self.scart.auto_commit() as session:
                sku = session.query(ProductSku).filter_by_({'SKUid': skuid}).first_('sku不存在')
                prid = sku.PRid
                product = session.query(Products).filter_by_({'PRid': prid}).first_('商品不存在')
                pbid = product.PBid
                if num <= 0:
                    raise ParamsError('num参数错误')
                cart = Carts.create({
                    'CAid': str(uuid.uuid4()),
                    'USid': usid,
                    'SKUid': skuid,
                    'CAnums': num,
                    'PBid': pbid,
                    'PRid': prid
                })
                msg = '添加购物车成功'
                session.add(cart)
        return Success(msg)

    @token_required
    def update(self):
        """更新购物车"""
        data = parameter_required(('caid', ))
        caid = data.get('caid')
        usid = request.user.id
        card = self.scart.get_card_one({'CAid': caid, 'USid': usid}, error='购物车不存在')  # card就是cart.
        # 默认的sku和数量
        skuid = data.get('skuid') or card.SKUid
        try:
            num = int(data.get('canums', card.CAnums))
            if num < 0:
                raise TypeError()
        except TypeError as e:
            raise ParamsError('num类型错误')
        msg = '更新成功'
        with self.scart.auto_commit() as session:
            # 数量为0执行删除
            if num == 0:
                session.query(Carts).filter_by({'CAid': caid}).delete_()
                msg = '删除成功'
            else:
                session.query(ProductSku).filter_by_({'SKUid': skuid}).first_('商品sku不存在')
                session.query(Carts).filter_by({'CAid': caid}).update({
                    'SKUid': skuid,
                    'CAnums': num
                })
        return Success(msg)

    @token_required
    def list(self):
        """个人购物车列表"""
        usid = request.user.id
        my_carts = self.scart.get_card_list({'USid': usid})
        pb_list = []
        new_cart_list = []
        product_num = 0
        for cart in my_carts:
            pbid = cart.PBid
            product = self.sproduct.get_product_by_prid(cart.PRid)  # 商品
            if not product:
                continue
            product.PRattribute = json.loads(product.PRattribute)
            pb = self.sproduct.get_product_brand_one({'PBid': pbid})
            if not pb:
                continue
            cart_sku = self.sproduct.get_sku_one({'SKUid': cart.SKUid})   # 购物车的sku
            if not cart_sku:
                continue
            cart_sku.SKUattriteDetail = json.loads(cart_sku.SKUattriteDetail)
            # skuvalue = self.sproduct.get_sku_value({'PRid': cart.PRid})   # 商品的skuvalue
            # 填充商品
            product.hide('PRdesc')
            product.fill('PRstatus_en', ProductStatus(product.PRstatus).name)
            # 商品sku
            skus = self.sproduct.get_sku({'PRid': product.PRid})
            sku_value_item = []
            for sku in skus:
                sku.SKUattriteDetail = json.loads(sku.SKUattriteDetail)
                sku_value_item.append(sku.SKUattriteDetail)
            product.fill('skus', skus)
            # 商品sku value
            sku_value_item_reverse = []
            for index, name in enumerate(product.PRattribute):
                value = list(set([attribute[index] for attribute in sku_value_item]))
                value = sorted(value)
                temp = {
                    'name': name,
                    'value': value
                }
                sku_value_item_reverse.append(temp)
            product.fill('SkuValue', sku_value_item_reverse)

            # 填充购物车
            cart.fill('sku', cart_sku)
            cart.fill('product', product)
            # 小计
            # cart.subtotal =
            # 数量
            product_num += 1
            # 店铺分组
            if pbid not in pb_list:
                new_cart_list.append({'cart': [cart], 'pb': pb})
                pb_list.append(pbid)
            else:
                index = pb_list.index(pbid)
                new_cart_list[index]['cart'].append(cart)
        return Success(data=new_cart_list).get_body(product_num=product_num)

    @token_required
    def destroy(self):
        """批量个人购物车"""
        data = parameter_required()
        usid = request.user.id
        caids = data.get('caids')
        if isinstance(caids, list) and len(caids) == 0:
            raise ParamsError('caids 为空')
        if not caids:
            caids = []
        if not isinstance(caids, list):
            raise ParamsError('caids 参数错误')
        # 删除
        with self.scart.auto_commit() as session:
            session.query(Carts).filter_(
                Carts.CAid.in_(caids),
                Carts.USid == usid
            ).delete_(synchronize_session=False)
        return Success('删除成功')





