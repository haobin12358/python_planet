# -*- coding: utf-8 -*-
import json
import random
import re
import time
import uuid
from datetime import datetime, timedelta
from decimal import Decimal

from flask import request, current_app
from sqlalchemy import extract

from planet.common.params_validates import parameter_required
from planet.common.error_response import ParamsError, SystemError, NotFound, StatusError, DumpliError, TokenError, \
    AuthorityError
from planet.common.request_handler import gennerc_log
from planet.common.success_response import Success
from planet.common.token_handler import token_required, is_admin, is_tourist
from planet.config.enums import PayType, Client, OrderFrom, OrderMainStatus, OrderRefundORAstate, \
    ApplyStatus, OrderRefundOrstatus, LogisticsSignStatus, DisputeTypeType, OrderEvaluationScore, \
    ActivityOrderNavigation
from planet.config.cfgsetting import ConfigSettings
from planet.control.CCoupon import CCoupon
from planet.control.CPay import CPay
from planet.extensions.register_ext import db
from planet.extensions.validates.trade import OrderListForm
from planet.models import ProductSku, Products, ProductBrand, AddressCity, ProductMonthSaleValue, UserAddress, User, \
    AddressArea, AddressProvince, CouponFor, TrialCommodity, UserCommission
from planet.models.trade import OrderMain, OrderPart, OrderPay, Carts, OrderRefundApply, LogisticsCompnay, \
    OrderLogistics, CouponUser, Coupon, OrderEvaluation, OrderCoupon, OrderEvaluationImage, OrderEvaluationVideo, \
    OrderRefund


class COrder(CPay, CCoupon):

    @token_required
    def list(self):
        form = OrderListForm().valid_data()
        usid = form.usid.data
        issaler = form.issaler.data  # 是否是卖家
        filter_args = form.omstatus.data  # 过滤参数
        omfrom = form.omfrom.data  # 来源
        if issaler:  # 卖家
            filter_args.append(OrderMain.PRcreateId == usid)  # todo
        else:
            filter_args.append(OrderMain.USid == usid)
        # 过滤下活动产生的订单
        if omfrom is None:
            filter_args.append(
                OrderMain.OMfrom.in_([OrderFrom.carts.value, OrderFrom.product_info.value])
            )
        else:
            filter_args.append(OrderMain.OMfrom == omfrom)
            filter_args.append(OrderMain.OMinRefund == False)
        order_mains = self.strade.get_ordermain_list(filter_args)

        for order_main in order_mains:
            order_parts = self.strade.get_orderpart_list({'OMid': order_main.OMid})
            for order_part in order_parts:
                order_part.SKUattriteDetail = json.loads(order_part.SKUattriteDetail)
                order_part.PRattribute = json.loads(order_part.PRattribute)
                # 状态
                # order_part.OPstatus_en = OrderPartStatus(order_part.OPstatus).name
                # order_part.add('OPstatus_en')

                # 如果是试用商品，订单信息中添加押金到期信息
                if order_main.OMfrom == OrderFrom.trial_commodity.value and order_main.OMstatus not in [
                                        OrderMainStatus.wait_pay.value, OrderMainStatus.cancle.value]:
                    # trialcommodity = TrialCommodity.query.filter_by_(TCid=order_part.PRid).first()
                    # deposit_expires = order_main.createtime + timedelta(days=trialcommodity.TCdeadline)
                    usercommission = UserCommission.query.filter_by(OPid=order_part.OPid).first()
                    deposit_expires = getattr(usercommission, 'UCendTime', '') or ''
                    order_main.fill('deposit_expires', deposit_expires)
                    order_part.fill('deposit_expires', deposit_expires)
            order_main.fill('order_part', order_parts)
            # 状态
            order_main.OMstatus_en = OrderMainStatus(order_main.OMstatus).name
            order_main.OMstatus_zh = OrderMainStatus(order_main.OMstatus).zh_value  # 汉字
            order_main.add('OMstatus_en', 'OMstatus_zh').hide('OPayno', 'USid', )
            order_main.fill('OMfrom_zh', OrderFrom(order_main.OMfrom).zh_value)
            # 用户
            # todo 卖家订单
            if is_admin():
                user = User.query.filter_by_({'USid': usid}).first_()
                if user:
                    user.fields = ['USname', 'USheader', 'USgender']
                    order_main.fill('user', user)
                # 主单售后状态信息
            if order_main.OMinRefund is True:
                omid = order_main.OMid
                order_refund_apply_instance = self._get_refund_apply({'OMid': omid})
                order_refund_apply_instance.fields = ['ORAproductStatus', 'ORAstatus', 'ORAstate',
                                                      'orastate_zh', 'ORAstatus_zh', 'ORAproductStatus_zh',
                                                      'createtime', 'ORAid']
                order_main.fill('order_refund_apply', order_refund_apply_instance)
                # 售后发货状态
                if order_refund_apply_instance.ORAstate == OrderRefundORAstate.goods_money.value and \
                        order_refund_apply_instance.ORAstatus == ApplyStatus.agree.value:
                    order_refund_instance = self._get_order_refund({'ORAid': order_refund_apply_instance.ORAid})
                    order_refund_instance.fields = ['ORstatus', 'ORstatus_zh', 'ORlogisticSignStatus_zh', 'createtime']
                    order_main.fill('order_refund', order_refund_instance)

        return Success(data=order_mains)

    @token_required
    def create(self):
        """创建并发起支付"""
        data = parameter_required(('info', 'omclient', 'omfrom', 'uaid', 'opaytype'))
        usid = request.user.id
        gennerc_log('current user is {}'.format(usid))
        uaid = data.get('uaid')
        opaytype = data.get('opaytype')
        try:
            omclient = int(data.get('omclient', Client.wechat.value))  # 下单设备
            omfrom = int(data.get('omfrom', OrderFrom.product_info.value))  # 商品来源
            Client(omclient)
            OrderFrom(omfrom)
        except Exception as e:
            raise ParamsError('客户端或商品来源错误')
        infos = data.get('info')
        with self.strade.auto_commit() as s:
            user = s.query(User).filter_by_({'USid': usid}).first_('无效用户')
            up1 = user.USopenid1
            up2 = user.USopenid2
            body = set()  # 付款时候需要使用的字段
            # 用户的地址信息
            user_address_instance = s.query(UserAddress).filter_by_({'UAid': uaid, 'USid': usid}).first_('地址信息不存在')
            omrecvphone = user_address_instance.UAphone
            areaid = user_address_instance.AAid
            # 地址拼接
            area, city, province = s.query(AddressArea, AddressCity, AddressProvince).filter(
                AddressArea.ACid == AddressCity.ACid, AddressCity.APid == AddressProvince.APid).filter(
                AddressArea.AAid == areaid).first_('地址有误')
            address = getattr(province, "APname", '') + getattr(city, "ACname", '') + getattr(
                area, "AAname", '')
            omrecvaddress = address + user_address_instance.UAtext
            omrecvname = user_address_instance.UAname
            opayno = self.wx_pay.nonce_str
            # model_bean = []
            mount_price = Decimal()  # 总价
            # # 实际佣金比
            # cfg = ConfigSettings()
            # level1commision = user.USCommission1 or cfg.get_item('commission', 'level1commision')
            # level2commision = user.USCommission2 or cfg.get_item('commission', 'level2commision')
            # 分订单
            for info in infos:
                order_price = Decimal()  # 订单实际价格
                order_old_price = Decimal()  # 原价格
                omid = str(uuid.uuid4())  # 主单id
                info = parameter_required(('pbid', 'skus', ), datafrom=info)
                pbid = info.get('pbid')
                skus = info.get('skus')
                coupons = info.get('coupons')
                ommessage = info.get('ommessage')
                product_brand_instance = s.query(ProductBrand).filter_by_({'PBid': pbid}).first_('品牌id: {}不存在'.format(pbid))
                prid_dict = {}  # 一个临时的prid字典
                order_part_list = []
                for sku in skus:
                    # 订单副单
                    opid = str(uuid.uuid4())
                    skuid = sku.get('skuid')
                    opnum = int(sku.get('nums', 1))
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
                        # 副单商品来源
                        'PRfrom': product_instance.PRfrom,
                        'UPperid': up1,
                        'UPperid2': up2,
                        # 'PRcreateId': product_instance.CreaterId
                    }
                    order_part_instance = OrderPart.create(order_part_dict)
                    order_part_list.append(order_part_instance)
                    # model_bean.append(order_part_instance)
                    s.add(order_part_instance)
                    s.flush()
                    # 订单价格计算
                    order_price += small_total
                    order_old_price += small_total
                    # 临时记录单品价格
                    prid_dict[prid] = prid_dict[prid] + small_total if prid in prid_dict else small_total
                    # 删除购物车
                    if omfrom == OrderFrom.carts.value:
                        s.query(Carts).filter_by({"USid": usid, "SKUid": skuid}).delete_()
                    # body 信息
                    body.add(product_instance.PRtitle)
                    # 对应商品销量 + num sku库存 -num
                    s.query(Products).filter_by_(PRid=prid).update({
                        'PRsalesValue': Products.PRsalesValue + opnum,
                    })
                    s.query(ProductSku).filter_by_(SKUid=skuid).update({
                        'SKUstock': ProductSku.SKUstock - opnum
                    })
                    # 月销量 修改或新增
                    today = datetime.now()
                    month_sale_updated = s.query(ProductMonthSaleValue).filter_(
                        ProductMonthSaleValue.PRid == prid,
                        extract('month', ProductMonthSaleValue.createtime) == today.month,
                        extract('year', ProductMonthSaleValue.createtime) == today.year
                    ).update({
                        'PMSVnum': ProductMonthSaleValue.PMSVnum + opnum
                    }, synchronize_session=False)
                    if not month_sale_updated:
                        month_sale_instance = ProductMonthSaleValue.create({
                            'PMSVid': str(uuid.uuid4()),
                            'PRid': prid,
                            'PMSVnum': opnum
                        })
                        # model_bean.append(month_sale_instance)
                        s.add(month_sale_instance)
                coupon_for_in_this = prid_dict.copy()
                # 使用优惠券
                if coupons:
                    for coid in coupons:
                        coupon_user = s.query(CouponUser).filter_by_({"COid": coid, 'USid': usid, 'UCalreadyUse': False}).first_('用户优惠券{}不存在'.format(coid))
                        coupon = s.query(Coupon).filter_by_({"COid": coupon_user.COid}).first_('优惠券不可用')
                        # 是否过期或者已使用过
                        can_use = self._isavalible(coupon, coupon_user)
                        if not can_use:
                            raise StatusError('优惠券已过期已使用')
                        # 是否可以在本订单使用
                        if coupon.COuseNum and coupons.count(coid) > coupon.COuseNum:
                            raise StatusError('叠加超出限制{}'.format(coid))

                        if coupon.COdownLine > order_old_price:
                            raise StatusError('未达到满减条件: {}'.format(coid))

                        # 优惠券使用对象
                        coupon_fors = self._coupon_for(coid)
                        coupon_for_pbids = self._coupon_for_pbids(coupon_fors)
                        if coupon_for_pbids:  # 品牌金额限制
                            if pbid not in coupon_for_pbids:
                                raise StatusError('优惠券{}仅可使用指定品牌'.format(coid))
                        coupon_for_prids = self._coupon_for_prids(coupon_fors)
                        if coupon_for_prids:
                            if not set(coupon_for_prids).intersection(set(prid_dict)):
                                raise StatusError('优惠券{}仅可用于指定商品'.format(coid))

                            # coupon_for_prids = [Decimal(str(v)) for k, v in prid_dict.items() if k in coupon_for_prids]
                            coupon_for_in_this = {
                                prid: Decimal(str(price)) for prid, price in coupon_for_in_this.items() if prid in coupon_for_prids
                            }
                            coupon_for_sum = sum(coupon_for_in_this.values())  # 优惠券支持的商品的总价
                            if coupon.COdownLine > coupon_for_sum:
                                raise StatusError('优惠券{}未达到指定商品满减'.format(coid))
                            reduce_price = coupon_for_sum * (1 - Decimal(str(coupon.COdiscount)) / 10) + Decimal(str(coupon.COsubtration))
                            order_price = order_price - reduce_price
                            if order_price <= 0:
                                order_price = 0.01

                            # 减少金额计算
                            # reduce_price = order_old_price - order_price
                        else:
                            coupon_for_sum = order_old_price
                            order_price = order_price * Decimal(str(coupon.COdiscount)) / 10 - Decimal(str(coupon.COsubtration))
                            reduce_price = order_old_price - order_price
                            if order_price <= 0:
                                order_price = 0.01
                        # 副单按照比例计算'实际价格'
                        for order_part in order_part_list:
                            if order_part.PRid in coupon_for_in_this:
                                order_part.OPsubTrueTotal = Decimal(order_part.OPsubTrueTotal) -\
                                                            (reduce_price * coupon_for_in_this[order_part.PRid] / coupon_for_sum)
                                if order_part.OPsubTrueTotal <= 0:
                                    order_part.OPsubTrueTotal = 0.01
                                s.add(order_part)
                                s.flush()

                        # 更改优惠券状态
                        coupon_user.UCalreadyUse = True
                        s.add(coupon_user)
                        # 优惠券使用记录
                        order_coupon_dict = {
                            'OCid': str(uuid.uuid4()),
                            'OMid': omid,
                            'COid': coid,
                            'OCreduce': reduce_price,
                        }
                        order_coupon_instance = OrderCoupon.create(order_coupon_dict)
                        s.add(order_coupon_instance)

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
                    'OMfreight': 0,  # 运费暂时为0
                    'OMmount': order_old_price,
                    'OMmessage': ommessage,
                    'OMtrueMount': order_price,
                    # 收货信息
                    'OMrecvPhone': omrecvphone,
                    'OMrecvName': omrecvname,
                    'OMrecvAddress': omrecvaddress,
                    # 'UPperid': user.USsupper1,
                    # 'UPperid2': user.USsupper2,
                    'UseCoupon': bool(coupons)
                }
                # if user.USsupper1:
                    # 主单佣金数据
                    # commision = user.USCommission
                    # total_comm = Commsion(order_price, commision).total_comm  # 佣金使用实付价格计算
                    # order_main_dict.setdefault('OMtotalCommision', total_comm)
                    # pass  # 佣金计算已修改
                order_main_instance = OrderMain.create(order_main_dict)
                s.add(order_main_instance)
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
            s.add(order_pay_instance)
            # s.add_all(model_bean)
        # 生成支付信息
        body = ''.join(list(body))
        openid = user.USopenid1 or user.USopenid2
        pay_args = self._pay_detail(omclient, opaytype, opayno, float(mount_price), body, openid=openid)
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
            # 副单售后状态信息
            if order_part.OPisinORA is True:
                opid = order_part.OPid
                order_refund_apply_instance = self._get_refund_apply({'OPid': opid})
                order_part.fill('order_refund_apply', order_refund_apply_instance)
                # 售后发货状态
                if order_refund_apply_instance.ORAstate == OrderRefundORAstate.goods_money.value and \
                        order_refund_apply_instance.ORAstatus == ApplyStatus.agree.value:
                    order_refund_instance = self._get_order_refund({'ORAid': order_refund_apply_instance.ORAid})
                    order_part.fill('order_refund', order_refund_instance)
        # 主单售后状态信息
        if order_main.OMinRefund is True:
            omid = order_main.OMid
            order_refund_apply_instance = self._get_refund_apply({'OMid': omid})
            order_main.fill('order_refund_apply', order_refund_apply_instance)
            # 售后发货状态
            if order_refund_apply_instance.ORAstate == OrderRefundORAstate.goods_money.value and \
                    order_refund_apply_instance.ORAstatus == ApplyStatus.agree.value:
                order_refund_instance = self._get_order_refund({'ORAid': order_refund_apply_instance.ORAid})
                order_main.fill('order_refund', order_refund_instance)
        order_main.fill('order_part', order_parts)
        # 状态
        order_main.OMstatus_en = OrderMainStatus(order_main.OMstatus).name
        order_main.OMstatus_zh = OrderMainStatus(order_main.OMstatus).zh_value
        order_main.add('OMstatus_en', 'createtime', 'OMstatus_zh').hide('OPayno', 'USid', )
        # 付款时间
        if order_main.OMstatus > OrderMainStatus.wait_pay.value:
            order_pay = OrderPay.query.filter_by_({'OPayno': order_main.OPayno}).first()
            order_main.fill('pay_time', order_pay.OPaytime)
        # 发货时间
        if order_main.OMstatus > OrderMainStatus.wait_send.value:
            order_logistics = OrderLogistics.query.filter_by_({'OMid': omid}).first()
            order_main.fill('send_time', order_logistics.createtime)
        return Success(data=order_main)

    @token_required
    def cancle(self):
        """付款前取消订单"""
        data = parameter_required(('omid', ))
        omid = data.get('omid')
        usid = request.user.id
        with self.strade.auto_commit() as s:
            s_list = []
            # 主单状态修改
            order_main = s.query(OrderMain).filter_by_({
                'OMid': omid,
                'USid': usid,
                'OMstatus': OrderMainStatus.wait_pay.value
            }).first_('指定订单不存在')
            order_main.OMstatus = OrderMainStatus.cancle.value
            s_list.append(order_main)
            # 优惠券返回
            if order_main.UseCoupon is True:
                order_coupons = s.query(OrderCoupon).filter_by_({'OMid': omid}).all()
                for order_coupon in order_coupons:
                    coupon_user_update = s.query(CouponUser).filter_by_({
                        'COid': order_coupon.COid,
                        'USid': usid,
                        'UCalreadyUse': True
                    }).update({'UCalreadyUse': False})
            # 库存修改
            order_parts = s.query(OrderPart).filter_by_({'OMid': omid}).all()
            for order_part in order_parts:
                skuid = order_part.SKUid
                opnum = order_part.OPnum
                s.query(ProductSku).filter_by_(SKUid=skuid).update({
                    'SKUstock': ProductSku.SKUstock + opnum
                })
            # 销量修改(暂不改)
        return Success('取消成功')

    @token_required
    def delete(self):
        """删除已取消的订单"""
        data = parameter_required(('omid', ))
        omid = data.get('omid')
        usid = request.user.id
        User.query.filter_by_(USid=usid).first_('用户不存在')
        order = OrderMain.query.filter_by_(OMid=omid).first_('订单不存在')
        assert order.OMstatus == OrderMainStatus.cancle.value, '只有已取消的订单可以删除'
        order.isdelete = True
        db.session.commit()
        return Success('删除成功', {'omid': omid})

    @token_required
    def create_order_evaluation(self):
        """创建订单评价"""
        usid = request.user.id
        user = User.query.filter(User.USid == usid).first_('token错误，无此用户信息')
        gennerc_log('user {0} is creating a evaluation'.format(user.USname))
        data = parameter_required(('evaluation', 'omid'))
        omid = data.get('omid')
        OrderMain.query.filter(OrderMain.OMid == omid, OrderMain.isdelete == False,
                               OrderMain.OMstatus == OrderMainStatus.wait_comment.value
                               ).first_('无此订单或当前状态不能进行评价')
        # 主单号包含的所有副单
        order_part_with_main = OrderPart.query.filter(OrderPart.OMid == omid, OrderPart.isdelete == False).all()
        orderpartid_list = []
        for op in order_part_with_main:
            orderpartid_list.append(op.OPid)
        evaluation_list = []
        oeid_list = []
        get_opid_list = []  # 从前端获取到的所有opid
        with self.strade.auto_commit() as oe:
            for evaluation in data['evaluation']:
                oeid = str(uuid.uuid1())
                evaluation = parameter_required(('opid', 'oescore'), datafrom=evaluation)
                opid = evaluation.get('opid')
                if opid in get_opid_list:
                    raise DumpliError('不能重复评论同一个订单商品')
                get_opid_list.append(opid)
                if opid not in orderpartid_list:
                    raise NotFound('无此订单商品信息')
                orderpartid_list.remove(opid)
                exist_evaluation = oe.query(OrderEvaluation).filter(OrderEvaluation.OPid == opid, OrderEvaluation.isdelete == False).first()
                if exist_evaluation:
                    raise StatusError('该订单已完成评价')
                oescore = evaluation.get('oescore', 5)
                if not re.match(r'^[1|2|3|4|5]$', str(oescore)):
                    raise ParamsError('oescore, 参数错误')
                order_part_info = oe.query(OrderPart).filter(OrderPart.OPid == opid, OrderPart.isdelete == False).first()
                evaluation_dict = OrderEvaluation.create({
                    'OEid': oeid,
                    'OMid': omid,
                    'USid': usid,
                    'OPid': opid,
                    'OEtext': evaluation.get('oetext', '此用户没有填写评价。'),
                    'OEscore': int(oescore),
                    'PRid': order_part_info.PRid,
                    'SKUattriteDetail': order_part_info.SKUattriteDetail
                })
                evaluation_list.append(evaluation_dict)
                # 商品总体评分变化
                try:
                    product_info = oe.query(Products).filter_by_(PRid=order_part_info.PRid).first()
                    average_score = round((float(product_info.PRaverageScore) + float(oescore) * 2) / 2)
                    oe.query(Products).filter_by_(PRid=order_part_info.PRid).update({'PRaverageScore': average_score})
                except Exception as e:
                    gennerc_log("order evaluation , update product score ERROR, is {}".format(e))
                image_list = evaluation.get('image')
                if image_list:
                    if len(image_list) > 5:
                        raise ParamsError('评价每次最多上传5张图片')
                    for image in image_list:
                        image_evaluation = OrderEvaluationImage.create({
                            'OEid': oeid,
                            'OEIid': str(uuid.uuid1()),
                            'OEImg': image.get('oeimg'),
                            'OEIsort': image.get('oeisort', 0)
                        })
                        evaluation_list.append(image_evaluation)
                video = evaluation.get('video')
                if video:
                    video_evaluation = OrderEvaluationVideo.create({
                        'OEid': oeid,
                        'OEVid': str(uuid.uuid1()),
                        'OEVideo': video.get('oevideo'),
                        'OEVthumbnail': video.get('oevthumbnail')
                    })
                    evaluation_list.append(video_evaluation)
                oeid_list.append(oeid)
            oe.add_all(evaluation_list)

        # 更改订单主单待评价状态为已完成
        update_status = self.strade.update_ordermain_one([OrderMain.OMid == omid, OrderMain.isdelete == False,
                                                          OrderMain.OMstatus == OrderMainStatus.wait_comment.value
                                                          ], {'OMstatus': OrderMainStatus.ready.value})
        if not update_status:
            raise StatusError('服务器繁忙 - 10001')

        # 如果提交时主单中还有未评价的副单，默认好评
        if len(orderpartid_list) > 0:
            other_evaluation_list = []
            with self.strade.auto_commit() as s:
                for i in orderpartid_list:
                    other_order_part_info = OrderPart.query.filter(OrderPart.OPid == i,
                                                                   OrderPart.isdelete == False
                                                                   ).first()
                    oeid = str(uuid.uuid1())
                    other_evaluation = OrderEvaluation.create({
                        'OEid': oeid,
                        'OMid': omid,
                        'USid': usid,
                        'OPid': i,
                        'OEtext': '此用户没有填写评价。',
                        'OEscore': 5,
                        'PRid': other_order_part_info.PRid,
                        'SKUattriteDetail': other_order_part_info.SKUattriteDetail
                    })
                    oeid_list.append(oeid)
                    other_evaluation_list.append(other_evaluation)
                    try:
                        # 商品总体评分变化
                        other_product_info = oe.query(Products).filter_by_(PRid=other_order_part_info.PRid).first()
                        other_average_score = round((float(other_product_info.PRaverageScore) + float(oescore) * 2) / 2)
                        oe.query(Products).filter_by_(PRid=other_product_info.PRid).update({'PRaverageScore': other_average_score})
                    except Exception as e:
                        gennerc_log("order evaluation , update product score ERROR, is {}".format(e))
                s.add_all(other_evaluation_list)
        return Success('评价成功', data={'oeid': oeid_list})

    def get_evaluation(self):
        """获取订单评价"""
        if not is_tourist():
            usid = request.user.id
            User.query.filter(User.USid == usid).first_('用户状态异常')
            tourist = 0
        else:
            tourist = 1
            usid = None
        args = parameter_required(('page_num', 'page_size'))
        prid = args.get('prid')
        my_post = args.get('my_post')
        if str(my_post) == '1':
            if not usid:
                raise TokenError()
            filter_args = {'USid': usid}
        else:
            parameter_required(('prid',))
            filter_args = {'PRid': prid}
        order_evaluation = self.strade.get_order_evaluation(filter_args)
        for order in order_evaluation:
            eva_user = User.query.filter(User.USid == order.USid).first()
            eva_user.fields = ['USname', 'USheader']
            order.fill('user', eva_user)
            order.SKUattriteDetail = json.loads(getattr(order, 'SKUattriteDetail') or '[]')
            image = self.strade.get_order_evaluation_image(order.OEid)
            video = self.strade.get_order_evaluation_video(order.OEid)
            zh_oescore = OrderEvaluationScore(order.OEscore).zh_value
            order.fill('zh_oescore', zh_oescore)
            order.fill('image', image)
            order.fill('video', video)
        return Success(data=order_evaluation).get_body(is_tourist=tourist)

    @token_required
    def del_evaluation(self):
        """删除订单评价"""
        usid = request.user.id
        user = User.query.filter(User.USid == usid, User.isdelete == False).first_('用户状态异常')
        gennerc_log('User {} delete order evaluation'.format(user.USname))
        data = parameter_required(('oeid',))
        oeid = data.get('oeid')
        order_eva = OrderEvaluation.query.filter_by_(OEid=oeid).first_('该评价已被删除')
        if usid != order_eva.USid:
            raise AuthorityError('只能删除自己发布的评价')
        del_eva = self.strade.del_order_evaluation(oeid)
        if not del_eva:
            raise SystemError('删除评价信息错误')
        self.strade.del_order_evaluation_image(oeid)
        self.strade.del_order_evaluation_video(oeid)
        return Success('删除成功', {'oeid': oeid})

    @token_required
    def get_order_count(self):
        """各状态订单的数量"""
        form = OrderListForm().valid_data()
        usid = form.usid.data
        issaler = form.issaler.data  # 是否是卖家
        extentions = form.extentions.data  # 是否扩展的查询
        ordertype = form.ordertype.data  # 区分活动订单
        if not issaler:
            filter_args = [OrderMain.USid == usid]
        else:
            # 是卖家, 卖家订单显示有问题..
            filter_args = [OrderMain.PRcreateId == usid]

        # 获取各类活动下的订单数量
        if ordertype == 'act':
            data = [
                {'count': self._get_act_order_count(filter_args, k),
                 'name': getattr(ActivityOrderNavigation, k).zh_value,
                 'omfrom': getattr(ActivityOrderNavigation, k).value}
                for k in ActivityOrderNavigation.all_member()
            ]
        else:
            # 去除一些活动订单数量
            # omfrom = form.omfrom.data
            # if omfrom is None:
            filter_args.append(
                OrderMain.OMfrom.in_([OrderFrom.carts.value, OrderFrom.product_info.value])
            )
            data = [  # 获取各状态的数量, '已完成'和'已取消'除外
                {'count': self._get_order_count(filter_args, k),
                 'name': getattr(OrderMainStatus, k).zh_value,
                 'status': getattr(OrderMainStatus, k).value}
                for k in OrderMainStatus.all_member() if k not in [
                    OrderMainStatus.ready.name, OrderMainStatus.cancle.name
                ]
            ]
            data.insert(  #
                0,
                {
                    'count': OrderMain.query.filter_(OrderMain.isdelete == False, *filter_args).count(),
                    'name': '全部',
                    'status': None
                }
            )
            if extentions == 'refund':
                data.append(  #
                    {
                        'count': OrderMain.query.filter_(OrderMain.OMinRefund == True, OrderMain.USid == usid,
                                                         OrderMain.OMfrom.in_(
                                                             [OrderFrom.carts.value, OrderFrom.product_info.value]
                                                         )).count(),
                        'name': '售后中',
                        'status': 40,  # 售后表示数字
                    }
                )
        return Success(data=data)

    @token_required
    def get_can_use_coupon(self):
        """获取可以使用的个人优惠券"""
        """

       "pbid": "pbid1",
        "skus": [
            {
                "skuid": "d64799ef-4477-4adb-a0de-b350cb2bc302",
                "nums": 6
            }
        ]
    }
        """
        usid = request.user.id
        with self.strade.auto_commit() as s:
            order_price = Decimal()  # 订单实际价格
            order_old_price = Decimal()  # 原价格
            info = parameter_required(('pbid', 'skus',))
            pbid = info.get('pbid')
            skus = info.get('skus')
            s.query(ProductBrand).filter_by_({'PBid': pbid}).first_('品牌id: {}不存在'.format(pbid))
            prid_dict = {}  # 一个临时的prid字典
            for sku in skus:
                # 订单副单
                skuid = sku.get('skuid')
                opnum = int(sku.get('nums', 1))
                assert opnum > 0
                sku_instance = s.query(ProductSku).filter_by_({'SKUid': skuid}).first_('skuid: {}不存在'.format(skuid))
                prid = sku_instance.PRid

                product_instance = s.query(Products).filter_by_({'PRid': prid}).first_(
                    'skuid: {}对应的商品不存在'.format(skuid))
                if product_instance.PBid != pbid:
                    raise ParamsError('品牌id: {}与skuid: {}不对应'.format(pbid, skuid))
                small_total = Decimal(str(sku_instance.SKUprice)) * opnum
                # 订单价格计算
                order_price += small_total
                order_old_price += small_total
                # 临时记录单品价格
                prid_dict[prid] = prid_dict[prid] + small_total if prid in prid_dict else small_total

            res = []
            coupon_users = s.query(CouponUser).filter_by_({'USid': usid, 'UCalreadyUse': False}).all()
            for coupon_user in coupon_users:
                coid = coupon_user.COid
                coupon = s.query(Coupon).filter_by_({"COid": coid}).first_()
                if not coupon:
                    continue
                # 是否过期或者已使用过
                can_use = self._isavalible(coupon, coupon_user)
                if not can_use:
                    continue
                if coupon.COdownLine > order_old_price:
                    continue
                # 优惠券使用对象
                coupon_fors = self._coupon_for(coid)
                coupon_for_pbids = self._coupon_for_pbids(coupon_fors)
                if coupon_for_pbids:  # 品牌金额限制
                    if pbid not in coupon_for_pbids:
                        continue
                coupon_for_prids = self._coupon_for_prids(coupon_fors)
                if coupon_for_prids:
                    if not set(coupon_for_prids).intersection(set(prid_dict)):
                        continue
                    coupon_for_sum = sum(
                        [Decimal(str(v)) for k, v in prid_dict.items() if k in coupon_for_prids])  # 优惠券支持的商品的总价
                    if coupon.COdownLine > coupon_for_sum:
                        continue
                    reduce_price = coupon_for_sum * (1 - Decimal(str(coupon.COdiscount)) / 10) + Decimal(str(coupon.COsubtration))

                else:
                    order_price = order_old_price * Decimal(str(coupon.COdiscount)) / 10 - Decimal(str(coupon.COsubtration))
                    reduce_price = order_old_price - order_price
                title_sub_title = self._title_subtitle(coupon)
                coupon.fill('title_subtitle', title_sub_title)
                res.append({
                    'coupon': coupon,
                    'reduce': float(reduce_price),
                })

        return Success(data=res)

    @token_required
    def confirm(self):
        """确认收货"""
        data = parameter_required(('omid',))
        omid = data.get('omid')
        usid = request.user.id
        order_main = OrderMain.query.filter_by_({
            'OMid': omid,
            'USid': usid,
            'OMstatus': OrderMainStatus.wait_recv.value
        }).first_('订单不存在或状态不正确')
        with db.auto_commit():
            # 改变订单状态
            order_main.OMstatus = OrderMainStatus.wait_comment.value
            db.session.add(order_main)
            # 佣金状态更改
            pass
        return Success('确认收货成功')

    @staticmethod
    def _get_order_count(arg, k):
        return OrderMain.query.filter_(OrderMain.OMstatus == getattr(OrderMainStatus, k).value,
                                       OrderMain.OMinRefund == False,
                                       OrderMain.isdelete == False,
                                       *arg
                                       ).count()

    @staticmethod
    def _get_act_order_count(arg, k):
        return OrderMain.query.filter_(OrderMain.OMfrom == getattr(ActivityOrderNavigation, k).value,
                                       OrderMain.OMinRefund == False,
                                       OrderMain.isdelete == False,
                                       *arg
                                       ).count()

    @staticmethod
    def _generic_omno():
        """生成订单号"""
        return str(time.strftime('%Y%m%d%H%M%S', time.localtime(time.time()))) +\
                 str(time.time()).replace('.', '')[-7:] + str(random.randint(1000, 9999))

    def _coupon_can_use_in_order(self, coupon, coupon_user, order_price):
        pass

    def _get_refund_apply(self, args):
        """获取售后申请"""
        order_refund_apply_instance = self.strade.get_orderrefundapply_one(args)
        order_refund_apply_instance.orastate_zh = OrderRefundORAstate(
            order_refund_apply_instance.ORAstate).zh_value  # 售后类型
        order_refund_apply_instance.ORAstatus_zh = ApplyStatus(
            order_refund_apply_instance.ORAstatus).zh_value  # 审核状态

        order_refund_apply_instance.ORAproductStatus_zh = DisputeTypeType(
            order_refund_apply_instance.ORAproductStatus).zh_value  # 是否收到货
        # order_refund_apply_instance.ORaddtionVoucher = json.loads(order_refund_apply_instance.ORaddtionVoucher)
        order_refund_apply_instance.add('orastate_zh', 'ORAstatus_zh', 'ORAproductStatus_zh', 'createtime')
        return order_refund_apply_instance

    def _get_order_refund(self, args):
        """获取售后发货状态"""
        order_refund_instance = OrderRefund.query.filter_by_(args).first_()
        order_refund_instance.ORstatus_zh = OrderRefundOrstatus(order_refund_instance.ORstatus).zh_value
        order_refund_instance.ORlogisticSignStatus_zh = LogisticsSignStatus(
            order_refund_instance.ORlogisticSignStatus).zh_value
        order_refund_instance.add('ORstatus_zh', 'ORlogisticSignStatus_zh', 'createtime')
        if order_refund_instance.ORlogisticCompany:
            logistic_company = LogisticsCompnay.query.filter_by_({
                'LCcode': order_refund_instance.ORlogisticCompany  # 快递中文
            }).first_()
            order_refund_instance.fill('orlogisticcompany_zh', logistic_company.LCname)

        return order_refund_instance

    def _coupon_for(self, coid):
        return CouponFor.query.filter_by({'COid': coid}).all(   )

    @staticmethod
    def _coupon_for_pbids(coupon_for):
        return [x.PBid for x in coupon_for if x.PBid]

    @staticmethod
    def _coupon_for_prids(coupon_for):
        return [x.PRid for x in coupon_for if x.PRid]

    def test_to_pay(self):
        """"""
        data = parameter_required(('phone',))
        phone = data.get('phone')
        with db.auto_commit():
            user = User.query.filter(
                User.UStelphone == phone
            ).first()
            current_app.logger.info('current test user is {}'.format(dict(user)))
            order_mains = OrderMain.query.filter_by({
                'USid': user.USid,
                "OMstatus": 0
            }).all()
            order_pay_instance = 0
            for order_main in order_mains:
                order_main.update({
                    'OMstatus': OrderMainStatus.wait_send.value
                })
                db.session.add(order_main)
                # 添加支付数据
                out_trade_no = order_main.OPayno
                order_pay_instance = OrderPay.query.filter_by({'OPayno': out_trade_no}).update({
                    'OPaytime': datetime.now(),
                    'OPaysn': self._generic_omno(),
                    'OPayJson': '{"hello": 1}'
                })

        return Success('success {}'.format(order_pay_instance))

    def test_to_send(self):
        data = parameter_required(('phone',))
        phone = data.get('phone')
        olcompany = 'YTO'
        olexpressno = '802725584022945412'
        user = User.query.filter(
            User.UStelphone == phone
        ).first()
        with self.strade.auto_commit() as s:
            order_mains = OrderMain.query.filter_by({
                'USid': user.USid,
                'OMstatus': OrderMainStatus.wait_send.value
            }).all()
            from flask import current_app
            current_app.logger.info('order main\' count is {}'.format(len(order_mains)))
            s_list = []
            for order_main_instance in order_mains:
                omid = order_main_instance.OMid
                if order_main_instance.OMstatus != OrderMainStatus.wait_send.value:
                    continue
                if order_main_instance.OMinRefund is True:
                    continue
                # 添加物流记录
                order_logistics_instance = OrderLogistics.create({
                    'OLid': str(uuid.uuid4()),
                    'OMid': omid,
                    'OLcompany': olcompany,
                    'OLexpressNo': olexpressno,
                })
                s_list.append(order_logistics_instance)
                # 更改主单状态
                order_main_instance.OMstatus = OrderMainStatus.wait_recv.value
                s_list.append(order_main_instance)
            s.add_all(s_list)
        return Success('success {}'.format(len(s_list)))

