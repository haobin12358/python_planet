# -*- coding: utf-8 -*-
import json
import random
import time
import uuid
from decimal import Decimal

from flask import request

from planet.common.params_validates import parameter_required
from planet.common.error_response import ParamsError, SystemError, NotFound
from planet.common.success_response import Success
from planet.common.token_handler import token_required
from planet.config.enums import PayType, Client, OrderFrom, OrderMainStatus
from planet.control.CPay import CPay
from planet.models import ProductSku, Products, ProductBrand
from planet.models.trade import OrderMain, OrderPart, OrderPay, Carts, OrderRefundApply


class COrder(CPay):

    @token_required
    def list(self):
        usid = request.user.id
        data = parameter_required()
        status = data.get('omstatus')
        order_mains = self.strade.get_ordermain_list({'USid': usid, 'OMstatus': status})
        for order_main in order_mains:
            order_parts = self.strade.get_orderpart_list({'OMid': order_main.OMid})
            for order_part in order_parts:
                order_part.SKUattriteDetail = json.loads(order_part.SKUattriteDetail)
                order_part.PRattribute = json.loads(order_part.PRattribute)
                # 状态
                # order_part.OPstatus_en = OrderPartStatus(order_part.OPstatus).name
                # order_part.add('OPstatus_en')
            order_main.fill('order_part', order_parts)
            # 状态
            order_main.OMstatus_en = OrderMainStatus(order_main.OMstatus).name
            order_main.add('OMstatus_en').hide('OPayno', 'USid', )
        return Success(data=order_mains)

    @token_required
    def create(self):
        """创建并发起支付"""
        data = parameter_required(('info', 'omclient', 'omfrom', 'udid', 'opaytype'))
        usid = request.user.id
        udid = data.get('udid')  # todo udid 表示用户的地址信息
        opaytype = data.get('opaytype')
        try:
            omclient = int(data.get('omclient', Client.wechat.value))  # 下单设备
            omfrom = int(data.get('omfrom', OrderFrom.carts.value))  # 商品来源
            Client(omclient)
            OrderFrom(omfrom)
        except Exception as e:
            raise ParamsError('客户端或商品来源错误')
        infos = data.get('info')
        with self.strade.auto_commit() as s:
            body = set()  # 付款时候需要使用的字段
            omrecvphone = '18753391801'
            omrecvaddress = '钱江世纪城'
            omrecvname = '老哥'
            opayno = self.wx_pay.nonce_str
            model_bean = []
            mount_price = Decimal()  # 总价
            for info in infos:
                order_price = Decimal()  # 订单价格
                omid = str(uuid.uuid4())  # 主单id
                info = parameter_required(('pbid', 'skus', ), datafrom=info)
                pbid = info.get('pbid')
                skus = info.get('skus')
                ommessage = info.get('ommessage')
                product_brand_instance = s.query(ProductBrand).filter_by_({'PBid': pbid}).first_('品牌id: {}不存在'.format(pbid))
                for sku in skus:
                    # 订单副单
                    opid = str(uuid.uuid4())
                    skuid = sku.get('skuid')
                    opnum = int(sku.get('opnum', 1))
                    assert opnum > 0
                    sku_instance = s.query(ProductSku).filter_by_({'SKUid': skuid}).first_('skuid: {}不存在'.format(skuid))
                    prid = sku_instance.PRid
                    product_instance = s.query(Products).filter_by_({'PRid': prid}).first_('skuid: {}对应的商品不存在'.format(skuid))
                    if product_instance.PBid != pbid:
                        raise ParamsError('品牌id: {}与skuid: {}不对应'.format(pbid, skuid))
                    small_total = Decimal(str(sku_instance.SKUprice)) * opnum
                    order_part_dict = {
                        'OMid': omid,
                        'OPid': opid,
                        'SKUid': skuid,
                        'PRattribute': product_instance.PRattribute,
                        'SKUattriteDetail': sku_instance.SKUattriteDetail,
                        'PRtitle': product_instance.PRtitle,
                        'SKUprice': sku_instance.SKUprice,
                        'PRmainpic': product_instance.PRmainpic,
                        'OPnum': opnum,
                        'PRid': product_instance.PRid,
                        'OPsubTotal': small_total,
                    }
                    order_part_instance = OrderPart.create(order_part_dict)
                    model_bean.append(order_part_instance)
                    # 订单价格计算
                    order_price += small_total
                    # 删除购物车
                    if omfrom == OrderFrom.carts.value:
                        s.query(Carts).filter_by_({"USid": usid, "SKUid": skuid}).delete_()
                    # body 信息
                    body.add(product_instance.PRtitle)
                    # 对应商品销量 + num sku库存 -num
                    s.query(Products).filter_by_(PRid=prid).update({
                        'PRsalesValue': Products.PRsalesValue + opnum,
                    })
                    s.query(ProductSku).filter_by_(SKUid=skuid).update({
                        'SKUstock': ProductSku.SKUstock - opnum
                    })
                # 主单
                order_main_dict = {
                    'OMid': omid,
                    'OMno': self._generic_omno(),
                    'OPayno': opayno,
                    'USid': usid,
                    'OMfrom': omfrom,
                    'PBname': product_brand_instance.PBname,
                    'PBid': pbid,
                    'OMclient': omclient,
                    'OMfreight': 0, # 运费暂时为0
                    'OMmount': order_price,
                    'OMmessage': ommessage,
                    'OMtrueMount': order_price,  # 暂时付费不优惠
                    # 收货信息
                    'OMrecvPhone': omrecvphone,
                    'OMrecvName': omrecvname,
                    'OMrecvAddress': omrecvaddress,
                }
                order_main_instance = OrderMain.create(order_main_dict)
                model_bean.append(order_main_instance)
                # 总价格累加
                mount_price += order_price
            # 支付数据表
            order_pay_dict = {
                'OPayid': str(uuid.uuid4()),
                'OPayno': opayno,
                'OPayType': opaytype,
                'OPayMount': mount_price,
            }
            order_pay_instance = OrderPay.create(order_pay_dict)
            model_bean.append(order_pay_instance)
            s.add_all(model_bean)
        # 生成支付信息
        body = ''.join(list(body))
        pay_args = self._pay_detail(omclient, opaytype, opayno, float(mount_price), body)
        response = {
            'pay_type': PayType(opaytype).name,
            'opaytype': opaytype,
            'args': pay_args
        }
        return Success('创建成功', data=response)

    @token_required
    def get(self):
        """单个订单"""
        data = parameter_required(('omid', ))
        omid = data.get('omid')
        order_main = self.strade.get_ordermain_one({'OMid': omid, 'USid': request.user.id}, '该订单不存在')
        order_parts = self.strade.get_orderpart_list({'OMid': omid})
        for order_part in order_parts:
            order_part.SKUattriteDetail = json.loads(order_part.SKUattriteDetail)
            order_part.PRattribute = json.loads(order_part.PRattribute)
            # 状态
            # order_part.OPstatus_en = OrderPartStatus(order_part.OPstatus).name
            # order_part.add('OPstatus_en')
            # 售后状态信息
            if order_part.OPisinORA:
                pass
        order_main.fill('order_part', order_parts)
        # 状态
        order_main.OMstatus_en = OrderMainStatus(order_main.OMstatus).name
        order_main.add('OMstatus_en').hide('OPayno', 'USid', )
        return Success(data=order_main)

    @token_required
    def cancle(self):
        """付款前取消订单"""
        data = parameter_required(('omid', ))
        omid = data.get('omid')
        usid = request.user.id
        with self.strade.auto_commit() as s:
            updated = s.query(OrderMain).filter_by_({
                'OMid': omid,
                'USid': usid,
                'OMstatus': OrderMainStatus.wait_pay.value
            }).update({
                'OMstatus': OrderMainStatus.cancle.value
            })
            if not updated:
                raise NotFound('指定订单不存在')
        return Success('取消成功')

    @staticmethod
    def _generic_omno():
        """生成订单号"""
        return str(time.strftime('%Y%m%d%H%M%S', time.localtime(time.time()))) +\
                 str(time.time()).replace('.', '')[-7:] + str(random.randint(1000, 9999))
