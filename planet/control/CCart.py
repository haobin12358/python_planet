# -*- coding: utf-8 -*-
import uuid

from flask import request

from planet.common.error_response import ParamsError
from planet.common.params_validates import parameter_required
from planet.common.success_response import Success
from planet.common.token_handler import token_required
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
        data = parameter_required(('caid', ))
        caid = data.get('caid')
        usid = request.user.id
        card = self.scart.get_card_one({'CAid': caid, 'USid': usid})
        # 默认的sku和数量
        skuid = data.get('skuid') or card.SKUid
        try:
            num = int(data.get('canums') or card.CAnums)
            if num <= 0:
                raise TypeError()
        except TypeError as e:
            raise ParamsError('num类型错误')

        with self.scart.auto_commit() as session:
            sku = session.query(ProductSku).filter_by_({'SKUid': skuid}).first_()
            session.query(Carts).filter_by_({'CAid': caid}).update({
                'SKUid': skuid,
                'CAnums': num
            })
        return Success('更新成功')








