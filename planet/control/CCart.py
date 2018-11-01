# -*- coding: utf-8 -*-
import json
import uuid

from flask import request

from planet.common.error_response import ParamsError
from planet.common.params_validates import parameter_required
from planet.common.success_response import Success
from planet.common.token_handler import token_required
from planet.config.enums import PRODUCT_STATUS
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
                sku = session.query(ProductSku).filter_by_({'SKUid': skuid}).first_()
                prid = sku.PRid
                product = session.query(Products).filter_by_({'PRid': prid}).first_()
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
        card = self.scart.get_card_one({'CAid': caid, 'USid': usid})  # card就是cart.
        # 默认的sku和数量
        skuid = data.get('skuid') or card.SKUid
        try:
            num = int(data.get('canums'))
            if num is None:
                num = card.CAnums
            if num < 0:
                raise TypeError()
        except TypeError as e:
            raise ParamsError('num类型错误')
        msg = '更新成功'
        with self.scart.auto_commit() as session:
            # 数量为0执行删除
            if num == 0:
                session.query(Carts).filter_by_({'CAid': caid}).delete_()
                msg = '删除成功'
            else:
                sku = session.query(ProductSku).filter_by_({'SKUid': skuid}).first_()
                session.query(Carts).filter_by_({'CAid': caid}).update({
                    'SKUid': skuid,
                    'CAnums': num
                })
        return Success(msg)

    @token_required
    def list(self):
        """个人购物车列表"""
        usid = request.user.id
        my_carts = self.scart.get_card_list({'USid': usid})
        for cart in my_carts:
            product = self.sproduct.get_product_by_prid(cart.PRid)  # 商品
            pb = self.sproduct.get_product_brand_one({'PBid': cart.PBid})
            cart_sku = self.sproduct.get_sku_one({'SKUid': cart.SKUid})   # 购物车的sku
            skuvalue = self.sproduct.get_sku_value({'PRid': cart.PRid})   # 商品的skuvalue
            product_skus = self.sproduct.get_sku({'PRid': cart.PRid})  # 商品的sku
            # 转json
            cart_sku.SKUdetail = json.loads(cart_sku.SKUdetail)
            for product_sku in product_skus:
                product_sku.SKUdetail = json.loads(product_sku.SKUdetail)
            skuvalue.PSKUvalue = json.loads(skuvalue.PSKUvalue)
            # 填充商品
            product.fill('skus', product_skus)
            product.fill('pskuvalue', skuvalue)
            product.hide('PRdesc')
            product.fill('PRstatus_zh', PRODUCT_STATUS.get(product.PRstatus))
            # 填充购物车
            cart.fill('sku', cart_sku)
            cart.fill('product', product)
            cart.fill('pb', pb)
            # 小计
            # cart.subtotal =
            # todo 店铺分组
        return Success(data=my_carts)

    @token_required
    def destroy(self):
        """清空个人购物车"""
        usid = request.user.id
        # 删除
        with self.scart.auto_commit() as session:
            session.query(Carts).filter_by_({'USid': usid}).delete_()
        return Success('清空成功')





