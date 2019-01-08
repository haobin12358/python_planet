# -*- coding: utf-8 -*-
import json
import random
import re
import time
import uuid
from datetime import datetime, timedelta, date
from decimal import Decimal

from flask import request, current_app
from sqlalchemy import extract, or_, and_, cast, Date, func

from planet.common.logistics import Logistics
from planet.common.params_validates import parameter_required
from planet.common.error_response import ParamsError, SystemError, NotFound, StatusError, DumpliError, TokenError, \
    AuthorityError, NotFound
from planet.common.request_handler import gennerc_log
from planet.common.success_response import Success
from planet.common.token_handler import token_required, is_admin, is_tourist, is_supplizer, admin_required
from planet.config.enums import PayType, Client, OrderFrom, OrderMainStatus, OrderRefundORAstate, \
    ApplyStatus, OrderRefundOrstatus, LogisticsSignStatus, DisputeTypeType, OrderEvaluationScore, \
    ActivityOrderNavigation, UserActivationCodeStatus, OMlogisticTypeEnum, ProductStatus, UserCommissionStatus, \
    UserIdentityStatus, ActivityRecvStatus
from planet.config.cfgsetting import ConfigSettings
from planet.control.CCoupon import CCoupon
from planet.control.CPay import CPay
from planet.extensions.register_ext import db
from planet.extensions.validates.trade import OrderListForm, HistoryDetailForm
from planet.models import ProductSku, Products, ProductBrand, AddressCity, ProductMonthSaleValue, UserAddress, User, \
    AddressArea, AddressProvince, CouponFor, TrialCommodity, ProductItems, Items, UserCommission, UserActivationCode, \
    UserSalesVolume, OutStock
from planet.models import OrderMain, OrderPart, OrderPay, Carts, OrderRefundApply, LogisticsCompnay, \
    OrderLogistics, CouponUser, Coupon, OrderEvaluation, OrderCoupon, OrderEvaluationImage, OrderEvaluationVideo, \
    OrderRefund, UserWallet, GuessAwardFlow, GuessNum, GuessNumAwardApply, MagicBoxFlow, MagicBoxOpen, MagicBoxApply, MagicBoxJoin


class COrder(CPay, CCoupon):

    @token_required
    def list(self):
        form = OrderListForm().valid_data()
        usid = form.usid.data
        omstatus = form.omstatus.data  # 过滤参数
        omfrom = form.omfrom.data  # 来源
        omno = form.omno.data
        omrecvname = form.omrecvname.data
        omrecvphone = form.omrecvphone.data
        prtitle = form.prtitle.data
        orastatus = form.orastatus.data
        orstatus = form.orstatus.data
        createtime_start = form.createtime_start.data
        createtime_end = form.createtime_end.data
        order_main_query = OrderMain.query.filter(OrderMain.isdelete == False)
        if usid:
            order_main_query = order_main_query.filter(OrderMain.USid == usid)
        # 过滤下活动产生的订单

        if omfrom is None:
            order_main_query = order_main_query.filter(
                OrderMain.OMfrom.in_([OrderFrom.carts.value, OrderFrom.product_info.value]))
        else:
            order_main_query = order_main_query.filter(
                OrderMain.OMfrom.in_(omfrom),
                OrderMain.OMinRefund == False
            )
        if omstatus == 'refund':
            # 后台获得售后订单(获取主单售后和附单售后)
            if is_admin() or is_supplizer():
                order_main_query = order_main_query.join(
                    OrderPart, OrderMain.OMid == OrderPart.OMid
                ).filter(
                    or_(and_(OrderPart.isdelete == False,
                             OrderPart.OPisinORA == True),
                        (OrderMain.OMinRefund == True))
                )

                if orastatus is not None:  # 售后的审核状态
                    order_main_query = order_main_query.filter(
                        or_(OrderMain.OMid == OrderRefundApply.OMid, OrderPart.OPid == OrderRefundApply.OPid),
                        OrderRefundApply.ORAstatus == orastatus,
                        OrderRefundApply.isdelete == False
                    )
                if orstatus is not None:  # 售后的物流状态
                    order_main_query = order_main_query.filter(
                        or_(OrderMain.OMid == OrderRefundApply.OMid, OrderPart.OPid == OrderRefundApply.OPid),
                        OrderRefundApply.ORAid == OrderRefund.ORAid,
                        OrderRefund.ORstatus == orstatus
                    )
            else:
                order_main_query = order_main_query.filter(
                    OrderMain.OMinRefund == True
                )

        elif omstatus:
            order_main_query = order_main_query.filter(*omstatus)
        if is_supplizer():
            # 供应商仅看自己出售的
            order_main_query = order_main_query.filter(
                OrderMain.PRcreateId == request.user.id
            )
        if omno:
            order_main_query = order_main_query.filter(OrderMain.OMno.contains(omno))
        if omrecvname:
            order_main_query = order_main_query.filter(OrderMain.OMrecvName.contains(omrecvname))
        if prtitle:
            if OrderPart not in order_main_query._joinpoint.values():
                order_main_query = order_main_query.join(OrderPart, OrderMain.OMid == OrderPart.OMid)
            order_main_query = order_main_query.filter(
                OrderPart.PRtitle.contains(prtitle)
            )
        if omrecvphone:
            order_main_query = order_main_query.filter(
                OrderMain.OMrecvPhone.contains(omrecvphone)
            )
        if createtime_start:
            order_main_query = order_main_query.filter(cast(OrderMain.createtime, Date) >= createtime_start)
        if createtime_end:
            order_main_query = order_main_query.filter(cast(OrderMain.createtime, Date) <= createtime_end)
        order_mains = order_main_query.order_by(OrderMain.createtime.desc()).all_with_page()
        for order_main in order_mains:
            order_parts = self.strade.get_orderpart_list({'OMid': order_main.OMid})
            for order_part in order_parts:
                order_part.SKUattriteDetail = json.loads(order_part.SKUattriteDetail)
                order_part.PRattribute = json.loads(order_part.PRattribute)
                # 状态
                if (is_supplizer() or is_admin()) and order_part.OPisinORA:
                    order_refund_apply_instance = self._get_refund_apply({'OPid': order_part.OPid})
                    self._fill_order_refund(order_part, order_refund_apply_instance, False)
                # 如果是试用商品，订单信息中添加押金到期信息
                if order_main.OMfrom == OrderFrom.trial_commodity.value and order_main.OMstatus not in [
                    OrderMainStatus.wait_pay.value, OrderMainStatus.cancle.value]:
                    usercommission = UserCommission.query.filter_by(OPid=order_part.OPid).first()
                    deposit_expires = getattr(usercommission, 'UCendTime', '') or ''
                    order_main.fill('deposit_expires', deposit_expires)
                    order_part.fill('deposit_expires', deposit_expires)
            order_main.fill('order_part', order_parts)
            # 状态
            order_main.OMstatus_en = OrderMainStatus(order_main.OMstatus).name
            order_main.OMstatus_zh = OrderMainStatus(order_main.OMstatus).zh_value  # 汉字
            order_main.add('OMstatus_en', 'OMstatus_zh', 'createtime').hide('OPayno', 'USid', )
            order_main.fill('OMfrom_zh', OrderFrom(order_main.OMfrom).zh_value)
            # 用户
            # todo 卖家订单
            if is_admin() or is_supplizer():
                user = User.query.filter_by_({'USid': usid}).first_()
                if user:
                    user.fields = ['USname', 'USheader', 'USgender']
                    order_main.fill('user', user)
                # 主单售后状态信息
            if order_main.OMinRefund is True:
                omid = order_main.OMid
                order_refund_apply_instance = self._get_refund_apply({'OMid': omid})
                self._fill_order_refund(order_main, order_refund_apply_instance, False)
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
            up1 = user.USsupper1
            up2 = user.USsupper2
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
            mount_price = Decimal()  # 总价
            omids = []
            # 采用激活码购买跳过支付参数
            if opaytype == PayType.codepay.value:
                activation_code = data.get('activation_code')
                if not activation_code:
                    raise ParamsError('请输入激活码')
                act_code = UserActivationCode.query.filter_by_({
                    'UACcode': activation_code,
                    'UACstatus': UserActivationCodeStatus.wait_use.value
                }).first_('激活码不可用')
                act_code.UACstatus = UserActivationCodeStatus.ready.value
                act_code.UACuseFor = usid
                act_code.UACtime = datetime.now()
                s.flush()
                self.__buy_upgrade_gift(
                    infos, s, omfrom, omclient, omrecvaddress,
                    omrecvname, omrecvphone, opaytype, activation_code)
                # 购买大礼包之后修改用户状态为已购买大礼包
                user.USlevel = UserIdentityStatus.toapply.value

                res = {
                    'pay_type': PayType(opaytype).name,
                    'opaytype': opaytype,
                    'args': 'codepay'
                }
                return Success('购买商品大礼包成功', data=res)
            # 分订单
            # todo 是否按照供应商拆分订单
            for info in infos:
                order_price = Decimal()  # 订单实际价格
                order_old_price = Decimal()  # 原价格
                omid = str(uuid.uuid1())  # 主单id
                omids.append(omid)
                info = parameter_required(('pbid', 'skus',), datafrom=info)
                pbid = info.get('pbid')
                skus = info.get('skus')
                coupons = info.get('coupons')
                ommessage = info.get('ommessage')
                product_brand_instance = s.query(ProductBrand).filter_by_({'PBid': pbid}).first_(
                    '品牌id: {}不存在'.format(pbid))
                prid_dict = {}  # 一个临时的prid字典
                order_part_list = []
                freight_list = []  # 快递费
                for sku in skus:
                    # 订单副单
                    opid = str(uuid.uuid1())
                    skuid = sku.get('skuid')
                    opnum = int(sku.get('nums', 1))
                    assert opnum > 0
                    sku_instance = s.query(ProductSku).filter_by_({'SKUid': skuid}).first_('skuid: {}不存在'.format(skuid))
                    prid = sku_instance.PRid
                    product_instance = s.query(Products).filter_by_({
                        'PRid': prid,
                        'PRstatus': ProductStatus.usual.value
                    }).first_('商品不存在或已下架')

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
                        'PRmainpic': sku_instance.SKUpic,
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
                    product_instance.PRsalesValue = product_instance.PRsalesValue + opnum
                    product_instance.PRstocks = product_instance.PRstocks - opnum
                    sku_instance.SKUstock = sku_instance.SKUstock - opnum
                    if sku_instance.SKUstock < 0:
                        raise StatusError('货源不足')
                    if product_instance.PRstocks <= 0:
                        product_instance.PRstatus = ProductStatus.sell_out.value
                    s.add(product_instance)
                    s.add(sku_instance)
                    s.flush()
                    current_app.logger.info('商品剩余库存: {}'.format(product_instance.PRstocks))
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
                            'PMSVid': str(uuid.uuid1()),
                            'PRid': prid,
                            'PMSVnum': opnum
                        })
                        # model_bean.append(month_sale_instance)
                        s.add(month_sale_instance)
                    # 是否是开店大礼包
                    item = Items.query.join(ProductItems, Items.ITid == ProductItems.ITid).filter(
                        Items.isdelete == False,
                        ProductItems.isdelete == False,
                        Items.ITid == 'upgrade_product',
                        ProductItems.PRid == prid,
                    ).first()
                    if item:
                        OMlogisticType = OMlogisticTypeEnum.online.value
                    else:
                        OMlogisticType = None

                    freight_list.append(product_instance.PRfreight)
                coupon_for_in_this = prid_dict.copy()
                # 使用优惠券
                if coupons:
                    for coid in coupons:
                        coupon_user = s.query(CouponUser).filter_by_(
                            {"COid": coid, 'USid': usid, 'UCalreadyUse': False}).first_('用户优惠券{}不存在'.format(coid))
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

                            coupon_for_in_this = {
                                prid: Decimal(str(price)) for prid, price in coupon_for_in_this.items() if
                                prid in coupon_for_prids
                            }
                            coupon_for_sum = sum(coupon_for_in_this.values())  # 优惠券支持的商品的总价
                            if coupon.COdownLine > coupon_for_sum:
                                raise StatusError('优惠券{}未达到指定商品满减'.format(coid))
                            reduce_price = coupon_for_sum * (1 - Decimal(str(coupon.COdiscount)) / 10) + Decimal(
                                str(coupon.COsubtration))
                            order_price = order_price - reduce_price
                            if order_price <= 0:
                                order_price = 0.01
                        else:
                            coupon_for_sum = order_old_price
                            order_price = order_price * Decimal(str(coupon.COdiscount)) / 10 - Decimal(
                                str(coupon.COsubtration))
                            reduce_price = order_old_price - order_price
                            if order_price <= 0:
                                order_price = 0.01
                        # 副单按照比例计算'实际价格'
                        for order_part in order_part_list:
                            if order_part.PRid in coupon_for_in_this:
                                order_part.OPsubTrueTotal = Decimal(order_part.OPsubTrueTotal) - \
                                                            (reduce_price * coupon_for_in_this[
                                                                order_part.PRid] / coupon_for_sum)
                                if order_part.OPsubTrueTotal <= 0:
                                    order_part.OPsubTrueTotal = 0.01
                                s.add(order_part)
                                s.flush()

                        # 更改优惠券状态
                        coupon_user.UCalreadyUse = True
                        s.add(coupon_user)
                        # 优惠券使用记录
                        order_coupon_dict = {
                            'OCid': str(uuid.uuid1()),
                            'OMid': omid,
                            'COid': coid,
                            'OCreduce': reduce_price,
                        }
                        order_coupon_instance = OrderCoupon.create(order_coupon_dict)
                        s.add(order_coupon_instance)
                # 快递费选最大
                freight = max(freight_list)
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
                    'OMfreight': freight,
                    'OMmount': order_old_price,
                    'OMmessage': ommessage,
                    'OMtrueMount': order_price + Decimal(str(freight)),
                    # 收货信息
                    'OMrecvPhone': omrecvphone,
                    'OMrecvName': omrecvname,
                    'OMrecvAddress': omrecvaddress,
                    'UseCoupon': bool(coupons),
                    'OMlogisticType': OMlogisticType,  # 发货类型, 如果为10 则 付款后直接完成
                    'PRcreateId': product_brand_instance.SUid,
                }
                order_main_instance = OrderMain.create(order_main_dict)
                s.add(order_main_instance)
                # 总价格累加
                mount_price += order_price

            # 支付数据表
            order_pay_dict = {
                'OPayid': str(uuid.uuid1()),
                'OPayno': opayno,
                'OPayType': opaytype,
                'OPayMount': mount_price,
            }
            order_pay_instance = OrderPay.create(order_pay_dict)
            s.add(order_pay_instance)
            # s.add_all(model_bean)
        from planet.extensions.tasks import auto_cancle_order

        auto_cancle_order.apply_async(args=omids, countdown=5 * 3600, expires=6 * 3600, )
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

    def get_order_feight(self):
        """获取获取快递费"""
        with self.strade.auto_commit() as s:
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
                prid_dict[prid] = product_instance.PRfreight
        feight = max([x for x in prid_dict.values()])
        return Success(data=feight)

    @token_required
    def get(self):
        """单个订单"""
        data = parameter_required(('omid',))
        omid = data.get('omid')
        if is_admin() or is_supplizer():
            order_main = self.strade.get_ordermain_one({'OMid': omid}, '该订单不存在')
        else:
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
                self._fill_order_refund(order_part, order_refund_apply_instance)
        # 主单售后状态信息
        if order_main.OMinRefund is True:
            omid = order_main.OMid
            order_refund_apply_instance = self._get_refund_apply({'OMid': omid})
            self._fill_order_refund(order_main, order_refund_apply_instance)
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
        try:
            if order_main.OMstatus > OrderMainStatus.wait_send.value:
                order_logistics = OrderLogistics.query.filter_by_({'OMid': omid}).first()
                order_main.fill('send_time', order_logistics.createtime)
        except AttributeError as e:
            current_app.logger.info('获取发货时间出现错误{}'.format(e))
            order_main.fill('send_time', datetime.now())
        return Success(data=order_main)

    @token_required
    def cancle(self):
        """付款前取消订单"""
        data = parameter_required(('omid',))
        omid = data.get('omid')
        usid = request.user.id
        order_main = OrderMain.query.filter_by_({
            'OMid': omid,
            # 'OMstatus': OrderMainStatus.wait_pay.value
        }).first_('指定订单不存在')
        if is_supplizer() and order_main.PRcreateId != usid:
            raise AuthorityError()
        if not is_admin() and not is_supplizer() and order_main.USid != usid:
            raise NotFound('订单订单不存在')
        self._cancle(order_main)
        return Success('取消成功')

    def _cancle(self, order_main):
        with db.auto_commit():
            # 主单状态修改
            order_main.OMstatus = OrderMainStatus.cancle.value
            omfrom = order_main.OMfrom
            omid = order_main.OMid
            db.session.add(order_main)
            # 优惠券返回
            if order_main.UseCoupon is True:
                order_coupons = OrderCoupon.query.filter_by_({'OMid': order_main.OMid}).all()
                for order_coupon in order_coupons:
                    coupon_user_update = CouponUser.query.filter_by_({
                        'COid': order_coupon.COid,
                        'USid': order_main.USid,
                        'UCalreadyUse': True
                    }).update({'UCalreadyUse': False})
            # 库存修改
            order_parts = OrderPart.query.filter_by_({'OMid': order_main.OMid}).all()
            for order_part in order_parts:
                skuid = order_part.SKUid
                opnum = order_part.OPnum
                prid = order_part.PRid
                sku_instance = ProductSku.query.filter(ProductSku.SKUid == skuid).first()
                product = Products.query.filter(Products.PRid == prid).first()
                # 库存修改
                if omfrom <= OrderFrom.product_info.value:
                    self._update_stock(opnum, product, sku_instance)
                elif omfrom == OrderFrom.guess_num_award.value:
                    pass
                    # guessawardflow = GuessAwardFlow.query.filter(
                    #     GuessAwardFlow.isdelete == False,
                    #     GuessAwardFlow.OMid == omid
                    # ).first()
                    # guess_num = GuessNum.query.filter(
                    #     GuessNum.GNid == guessawardflow.GNid
                    # ).first()
                    # apply = GuessNumAwardApply.query.filter(
                    #     GuessNumAwardApply.isdelete == False,
                    #     GuessNumAwardApply.GNAAid == guess_num.GNNAid
                    # ).update({
                    #     'SKUstock': GuessNumAwardApply.SKUstock + opnum
                    # })
                    #
                    # stock = OutStock.query.join(
                    #     GuessNumAwardApply, GuessNumAwardApply.
                    # ).filter(
                    #     OutStock.isdelete == False,
                    # )
                    # guessawardflow.GFAstatus = ActivityRecvStatus.wait_recv.value
                    # db.session.add(guessawardflow)
                elif omfrom == OrderFrom.fresh_man.value:
                    # todo
                    pass
                elif omfrom == OrderFrom.magic_box.value:
                    current_app.logger.info('活动魔盒订单')
                    magic_box_flow = MagicBoxFlow.query.filter(
                        MagicBoxFlow.OMid == omid,
                    ).first()
                    magic_box_join = MagicBoxJoin.query.filter(
                        MagicBoxJoin.MBJid == magic_box_flow.MBJid
                    ).first()
                    magic_box_join.MBJstatus = ActivityRecvStatus.wait_recv.value
                    db.session.add(magic_box_join)
                    current_app.logger.info('改魔盒的领取状态{}'.format(dict(magic_box_join)))
                    db.session.add(magic_box_join)
                    magic_box_apply = MagicBoxApply.query.filter(
                        MagicBoxApply.isdelete == False,
                        MagicBoxApply.MBAid == magic_box_join.MBAid
                    ).first()
                    current_app.logger.info('osid is {}'.format(magic_box_apply.OSid))
                    out_stock = OutStock.query.filter(OutStock.isdelete == False, OutStock.OSid == magic_box_apply.OSid).first()
                    if out_stock:
                        out_stock.update({
                            'OSnum': OutStock.OSnum + opnum
                        })
                        current_app.logger.info('魔盒取消订单, 增加库存{}, 当前 {}'.format(opnum, out_stock.OSnum))
                        db.session.add(out_stock)
                    db.session.flush()
                    # todo 库存操作

    @token_required
    def delete(self):
        """删除已取消的订单"""
        data = parameter_required(('omid',))
        omid = data.get('omid')
        usid = request.user.id
        with db.auto_commit():
            User.query.filter_by_(USid=usid).first_('用户不存在')
            order = OrderMain.query.filter_by_(OMid=omid).first_('订单不存在')
            assert order.OMstatus == OrderMainStatus.cancle.value, '只有已取消的订单可以删除'
            order.isdelete = True
        return Success('删除成功', {'omid': omid})

    @token_required
    def create_order_evaluation(self):
        """创建订单评价"""
        usid = request.user.id
        user = User.query.filter(User.USid == usid).first_('token错误，无此用户信息')
        usname, usheader = user.USname, user.USheader
        current_app.logger.info('User {0} created order evaluations'.format(user.USname))
        data = parameter_required(('evaluation', 'omid'))
        omid = data.get('omid')
        om = OrderMain.query.filter(OrderMain.OMid == omid, OrderMain.isdelete == False,
                                    OrderMain.OMstatus == OrderMainStatus.wait_comment.value
                                    ).first_('无此订单或当前状态不能进行评价')
        # 主单号包含的所有副单
        order_part_with_main = OrderPart.query.filter(OrderPart.OMid == omid, OrderPart.isdelete == False).all()
        evaluation_instance_list = list()
        oeid_list = list()
        get_opid_list = list()  # 从前端获取到的所有opid
        with db.auto_commit():
            orderpartid_list = [self._commsion_into_count(x) for x in order_part_with_main]
            self._tosalesvolume(om.OMtrueMount, usid)  # 销售额统计
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
                exist_evaluation = OrderEvaluation.query.filter(OrderEvaluation.OPid == opid,
                                                                OrderEvaluation.isdelete == False).first()
                if exist_evaluation:
                    raise StatusError('该订单已完成评价')
                oescore = evaluation.get('oescore', 5)
                if not re.match(r'^[1|2|3|4|5]$', str(oescore)):
                    raise ParamsError('oescore, 参数错误')
                order_part_info = OrderPart.query.filter(OrderPart.OPid == opid, OrderPart.isdelete == False).first()
                evaluation_dict = OrderEvaluation.create({
                    'OEid': oeid,
                    'OMid': omid,
                    'USid': usid,
                    'USname': usname,
                    'USheader': usheader,
                    'OPid': opid,
                    'OEtext': evaluation.get('oetext', '此用户没有填写评价。'),
                    'OEscore': int(oescore),
                    'PRid': order_part_info.PRid,
                    'SKUattriteDetail': order_part_info.SKUattriteDetail
                })
                evaluation_instance_list.append(evaluation_dict)
                # 商品总体评分变化
                try:
                    product_info = Products.query.filter_by_(PRid=order_part_info.PRid).first()
                    average_score = round((float(product_info.PRaverageScore) + float(oescore) * 2) / 2)
                    Products.query.filter_by_(PRid=order_part_info.PRid).update({'PRaverageScore': average_score})
                except Exception as e:
                    gennerc_log("Evaluation ERROR: Update Product Score OPid >>> {0}, ERROR >>> {1}".format(opid, e))
                # 评价中的图片
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
                        evaluation_instance_list.append(image_evaluation)
                # 评价中的视频
                video = evaluation.get('video')
                if video:
                    video_evaluation = OrderEvaluationVideo.create({
                        'OEid': oeid,
                        'OEVid': str(uuid.uuid1()),
                        'OEVideo': video.get('oevideo'),
                        'OEVthumbnail': video.get('oevthumbnail')
                    })
                    evaluation_instance_list.append(video_evaluation)
                oeid_list.append(oeid)

            # 更改订单主单中待评价状态为已完成
            update_status = OrderMain.query.filter(OrderMain.OMid == omid, OrderMain.isdelete == False,
                                                   OrderMain.OMstatus == OrderMainStatus.wait_comment.value
                                                   ).update({'OMstatus': OrderMainStatus.ready.value})
            if not update_status:
                current_app.logger.info("Order Evaluation Update Main Status Error, OMid is >>> {}".format(omid))

            # 如果提交时主单还有未评价的副单，默认好评
            if len(orderpartid_list) > 0:
                for order_part_id in orderpartid_list:
                    other_order_part_info = OrderPart.query.filter(
                        OrderPart.OPid == order_part_id,
                        OrderPart.isdelete == False
                    ).first()
                    oeid = str(uuid.uuid1())
                    other_evaluation = OrderEvaluation.create({
                        'OEid': oeid,
                        'OMid': omid,
                        'USid': usid,
                        'USname': usname,
                        'USheader': usheader,
                        'OPid': order_part_id,
                        'OEtext': '此用户没有填写评价。',
                        'OEscore': 5,
                        'PRid': other_order_part_info.PRid,
                        'SKUattriteDetail': other_order_part_info.SKUattriteDetail
                    })
                    oeid_list.append(oeid)
                    evaluation_instance_list.append(other_evaluation)
                    try:
                        # 商品总体评分变化
                        other_product_info = Products.query.filter_by_(PRid=other_order_part_info.PRid).first()
                        other_average_score = round((float(other_product_info.PRaverageScore) + float(oescore) * 2) / 2)
                        Products.query.filter_by_(PRid=other_product_info.PRid).update(
                            {'PRaverageScore': other_average_score})
                    except Exception as e:
                        gennerc_log("Other Evaluation ERROR: Update Product Score OPid >>> {0}, "
                                    "ERROR >>> {1}".format(order_part_id, e))
            db.session.add_all(evaluation_instance_list)
        return Success('评价成功', data={'oeid': oeid_list})

    @admin_required
    def set_autoevaluation_time(self):
        """设置自动评价超过x天的订单：x"""
        data = parameter_required(('day',))
        day = data.get('day', 7)
        cfs = ConfigSettings()
        cfs.set_item('autoevaluateparams', 'day', str(day))
        return Success('设置成功', {'day': day})

    @admin_required
    def get_autoevaluation_time(self):
        """获取自动评价超过x天的订单：x"""
        cfs = ConfigSettings()
        day = cfs.get_item('autoevaluateparams', 'day')
        return Success('获取成功', {'day': day})

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
            if order.USname and order.USheader:
                eva_user = {'usname': order['USname'], 'usheader': order['USheader']}
            else:
                eva_user = User.query.filter(User.USid == order.USid).first()
                if eva_user:
                    eva_user.fields = ['USname', 'USheader']
                else:
                    eva_user = {'usname': '神秘的客官', 'usheader': ''}
            order.fill('user', eva_user)
            order.SKUattriteDetail = json.loads(getattr(order, 'SKUattriteDetail') or '[]')
            image = self.strade.get_order_evaluation_image(order.OEid)
            video = self.strade.get_order_evaluation_video(order.OEid)
            zh_oescore = OrderEvaluationScore(order.OEscore).zh_value
            order.hide('USid', 'USname', 'USheader')
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
        extentions = form.extentions.data  # 是否扩展的查询
        ordertype = form.ordertype.data  # 区分活动订单
        filter_args = []
        if usid:
            filter_args.append(OrderMain.USid == usid)
        if is_supplizer():
            # 是卖家, 卖家订单显示有问题..
            filter_args.append(OrderMain.PRcreateId == request.user.id)
        # 获取各类活动下的订单数量
        if ordertype == 'act':
            act_value = [getattr(ActivityOrderNavigation, k).value for k in ActivityOrderNavigation.all_member()]
            data = [
                {'count': self._get_act_order_count(filter_args, k),
                 'name': getattr(ActivityOrderNavigation, k).zh_value,
                 'omfrom': getattr(ActivityOrderNavigation, k).value}
                for k in ActivityOrderNavigation.all_member()
            ]
            # 全部
            if is_supplizer() or is_admin():
                data.insert(  #
                    0, {
                        'count': OrderMain.query.filter_(OrderMain.isdelete == False,
                                                         OrderMain.OMfrom.in_(act_value),
                                                         *filter_args).distinct().count(),
                        'name': '全部',
                        'omfrom': ','.join(list(map(str, act_value)))
                    }
                )
        else:
            filter_args.append(
                OrderMain.OMfrom.in_([OrderFrom.carts.value, OrderFrom.product_info.value])
            )
            if not is_admin() and not is_supplizer():
                data = [  # 获取各状态的数量, '已完成'和'已取消'除外
                    {'count': self._get_order_count(filter_args, k),
                     'name': getattr(OrderMainStatus, k).zh_value,
                     'status': getattr(OrderMainStatus, k).value}
                    for k in OrderMainStatus.all_member() if k not in [
                        OrderMainStatus.ready.name, OrderMainStatus.cancle.name
                    ]
                ]
            else:
                data = [  # 获取各状态的数量
                    {'count': self._get_order_count(filter_args, k),
                     'name': getattr(OrderMainStatus, k).zh_value,
                     'status': getattr(OrderMainStatus, k).value}
                    for k in OrderMainStatus.all_member()
                ]
            data.insert(  #
                0, {
                    'count': OrderMain.query.filter_(OrderMain.isdelete == False, *filter_args).distinct().count(),
                    'name': '全部',
                    'status': None
                }
            )
            if extentions == 'refund':
                if not is_admin() and not is_supplizer():
                    refund_count = OrderMain.query.filter_(OrderMain.OMinRefund == True,
                                                           OrderMain.USid == usid,
                                                           OrderMain.isdelete == False,
                                                           OrderMain.OMfrom.in_(
                                                               [OrderFrom.carts.value, OrderFrom.product_info.value]),
                                                           *filter_args).distinct().count()
                else:
                    refund_count = OrderMain.query.join(OrderPart, OrderPart.OMid == OrderMain.OMid).filter_(
                        OrderMain.isdelete == False,
                        or_(and_(OrderPart.isdelete == False,
                                 OrderPart.OPisinORA == True),
                            (OrderMain.OMinRefund == True)),
                        OrderMain.OMfrom.in_([OrderFrom.carts.value, OrderFrom.product_info.value]),
                        *filter_args).distinct().count()
                data.append(  #
                    {
                        'count': refund_count,
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
                    reduce_price = coupon_for_sum * (1 - Decimal(str(coupon.COdiscount)) / 10) + Decimal(
                        str(coupon.COsubtration))

                else:
                    order_price = order_old_price * Decimal(str(coupon.COdiscount)) / 10 - Decimal(
                        str(coupon.COsubtration))
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

    @token_required
    def history_detail(self):
        if not is_supplizer() and not is_admin():
            raise AuthorityError()
        form = HistoryDetailForm().valid_data()
        days = form.days.data
        if days:
            days = days.replace(' ', '').split(',')
            days = list(map(lambda x: datetime.strptime(x, '%Y-%m-%d').date(), days))
        else:
            days = []
        suid = request.user.id if is_supplizer() else None
        datas = []
        for day in days:
            data = {
                'day_total': self._history_order('total', day=day,
                                                 status=OrderMain.OMstatus > OrderMainStatus.wait_pay.value,
                                                 suid=suid),
                'day_count': self._history_order('count', day=day, suid=suid),
                'wai_pay_count': self._history_order('count', day=day,
                                                     status=OrderMain.OMstatus == OrderMainStatus.wait_pay.value,
                                                     suid=suid),
                'in_refund': self._inrefund(day=day, suid=suid),
                'day': day
            }
            datas.append(data)
        if not days:
            # 获取系统全部
            data = {
                'day_total': self._history_order('total',
                                                 status=OrderMain.OMstatus > OrderMainStatus.wait_pay.value,
                                                 suid=suid),
                'day_count': self._history_order('count', suid=suid),
                'wai_pay_count': 0,
                'in_refund': 0,
                'day': None
            }
            datas.append(data)
        return Success(data=datas)

    def _history_order(self, *args, **kwargs):
        with db.auto_commit() as session:
            status = kwargs.get('status', None)
            day = kwargs.get('day', None)
            suid = kwargs.get('suid', None)
            if 'total' in args:
                query = session.query(func.sum(OrderMain.OMtrueMount))
            elif 'count' in args:
                query = session.query(func.count(OrderMain.OMid))
            elif 'refund' in args:
                return self._inrefund(*args, **kwargs)
            query = query.filter(OrderMain.isdelete == False)
            if status is not None:
                query = query.filter(status)
            if day is not None:
                query = query.filter(
                    cast(OrderMain.createtime, Date) == day,
                )
            if suid is not None:
                query = query.filter(OrderMain.PRcreateId == suid)
            return query.first()[0] or 0

    def _inrefund(self, *args, **kwargs):
        suid = kwargs.get('suid')
        day = kwargs.get('day')
        query = OrderMain.query.join(OrderPart, OrderPart.OMid == OrderMain.OMid).filter_(
            OrderMain.isdelete == False,
            or_(and_(OrderPart.isdelete == False,
                     OrderPart.OPisinORA == True),
                (OrderMain.OMinRefund == True)),
            OrderMain.OMfrom.in_([OrderFrom.carts.value, OrderFrom.product_info.value]))
        if day:
            query = query.filter(
                or_(OrderRefundApply.OMid == OrderMain.OMid,
                    OrderRefundApply.OPid == OrderPart.OPid),
            )
            query = query.filter(
                cast(OrderRefundApply.createtime, Date) == day,
            )
        if suid:
            query = query.filter(OrderMain.PRcreateId == suid)
        return query.group_by(OrderMain.OMid).count()

    def _tosalesvolume(self, amount, usid):
        today = datetime.today()
        user = User.query.filter_by_(USid=usid).first_('订单数据异常')
        if user.USsupper1:
            usv = UserSalesVolume.query.filter(
                UserSalesVolume.isdelete == False,
                extract('month', UserSalesVolume.createtime) == today.month,
                extract('year', UserSalesVolume.createtime) == today.year,
                UserSalesVolume.USid == user.USsupper1
            ).first()
            if not usv:
                usv = UserSalesVolume.create({
                    'USVid': str(uuid.uuid1()),
                    'USid': user.USsupper1,
                    'USVamount': 0
                })
                db.session.add(usv)
            usv.USVamount = float('%.2f' % (float(amount) + float(usv.USVamount)))

    @staticmethod
    def _get_order_count(arg, k):
        return OrderMain.query.filter_(OrderMain.OMstatus == getattr(OrderMainStatus, k).value,
                                       OrderMain.OMinRefund == False,
                                       OrderMain.isdelete == False,
                                       *arg
                                       ).distinct().count()

    @staticmethod
    def _get_act_order_count(arg, k):
        return OrderMain.query.filter_(OrderMain.OMfrom == getattr(ActivityOrderNavigation, k).value,
                                       OrderMain.OMinRefund == False,
                                       OrderMain.isdelete == False,
                                       *arg
                                       ).distinct().count()

    @staticmethod
    def _generic_omno():
        """生成订单号"""
        return str(time.strftime('%Y%m%d%H%M%S', time.localtime(time.time()))) + \
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
        return CouponFor.query.filter_by({'COid': coid}).all()

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

    def update_price(self):
        """订单付款前改价格"""
        # 修改后附单价格处理 佣金需要调整
        if not is_supplizer() and not is_admin():
            raise AuthorityError()
        data = parameter_required(('omid', 'price'))
        omid = data.get('omid')
        price = data.get('price')
        try:
            price = float(price)
            if price <= 0:
                raise TypeError()
            price = round(price, 2)
        except TypeError:
            raise ParamsError('价格参数不正确')
        order_main = OrderMain.query.filter(
            OrderMain.isdelete == False,
            OrderMain.OMid == omid
        ).first_('订单不存在')
        if is_supplizer() and order_main.PRcreateId != request.user.id:
            raise AuthorityError()
        if order_main.OMstatus != OrderMainStatus.wait_pay.value:
            raise StatusError('订单{}'.format(OrderMainStatus(order_main.OMstatus).zh_value))
        with db.auto_commit():
            order_main.OMtrueMount = price
            db.session.add(order_main)
        return Success('修改成功')

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
                    'OLid': str(uuid.uuid1()),
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

    def __buy_upgrade_gift(self, infos, s, omfrom, omclient, omrecvaddress,
                           omrecvname, omrecvphone, opaytype, activation_code):
        mount_price = Decimal()
        for info in infos:
            order_price = Decimal()  # 订单实际价格
            order_old_price = Decimal()  # 原价格
            info = parameter_required(('pbid', 'skus',), datafrom=info)
            pbid = info.get('pbid')
            skus = info.get('skus')
            omid = str(uuid.uuid1())  # 主单id
            ommessage = info.get('ommessage')
            prid_dict = {}  # 一个临时的prid字典
            product_brand_instance = s.query(ProductBrand).filter_by_({'PBid': pbid}).first_(
                '品牌id: {}不存在'.format(pbid))

            order_part_list = []
            for sku in skus:
                # 订单副单
                opid = str(uuid.uuid1())
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
                    # 'UPperid': up1,
                    # 'UPperid2': up2,
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
                    s.query(Carts).filter_by({"USid": request.user.id, "SKUid": skuid}).delete_()

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
                        'PMSVid': str(uuid.uuid1()),
                        'PRid': prid,
                        'PMSVnum': opnum
                    })

                    s.add(month_sale_instance)

            order_main_dict = {
                'OMid': omid,
                'OMno': self._generic_omno(),
                # 'OPayno': opayno,
                'USid': request.user.id,
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
                'UseCoupon': False,
                'OMstatus': OrderMainStatus.ready.value,
                'OMlogisticType': OMlogisticTypeEnum.online.value
            }
            order_main_instance = OrderMain.create(order_main_dict)
            s.add(order_main_instance)
            mount_price += order_price
            # 发货表
            orderlogistics = OrderLogistics.create({
                'OLid': str(uuid.uuid1()),
                'OMid': omid,
                'OLcompany': 'auto',
                'OLexpressNo': self._generic_omno(),
                'OLsignStatus': LogisticsSignStatus.already_signed.value,
                'OLdata': '[]',
                'OLlastresult': '{}'
            })
            s.add(orderlogistics)
        # 支付数据表
        order_pay_dict = {
            'OPayid': str(uuid.uuid1()),
            'OPayno': activation_code,
            'OPayType': opaytype,
            'OPayMount': mount_price,
            'OPaytime': datetime.now(),
        }
        order_pay_instance = OrderPay.create(order_pay_dict)
        s.add(order_pay_instance)

    def _commsion_into_count(self, order_part):
        """佣金到账"""
        opid = order_part.OPid
        if order_part.OPisinORA:
            return opid
        # 佣金到账
        user_commisions = UserCommission.query.filter(
            UserCommission.isdelete == False,
            UserCommission.OPid == opid
        ).all()
        for user_commision in user_commisions:
            user_commision.update({
                'UCstatus': UserCommissionStatus.in_account.value
            })
            db.session.add(user_commision)
            # 余额
            user_wallet = UserWallet.query.filter(
                UserWallet.isdelete == False,
                UserWallet.USid == user_commision.USid,
                UserWallet.CommisionFor == user_commision.CommisionFor
            ).first()
            if user_wallet:
                user_wallet.UWbalance += user_commision.UCcommission
                user_wallet.UWtotal += user_commision.UCcommission
                user_wallet.UWcash += user_commision.UCcommission
                db.session.add(user_wallet)
            else:
                user_wallet_instance = UserWallet.create({
                    'UWid': str(uuid.uuid1()),
                    'USid': user_commision.USid,
                    'UWbalance': user_commision.UCcommission,
                    'UWtotal': user_commision.UCcommission,
                    'UWcash': user_commision.UCcommission,
                    'CommisionFor': user_commision.CommisionFor
                })
                db.session.add(user_wallet_instance)
            current_app.logger.info('佣金到账数量 {}'.format(user_commision))
        return opid

    def _fill_order_refund(self, o, apply, detail=True):
        """
        填充售后物流等相关信息
        :param o: 主单或附单对象
        :param apply: 对应的申请单对象
        :return:
        """
        # order_refund_apply_instance = self._get_refund_apply({'OPid': opid})
        o.fill('order_refund_apply', apply)
        # 售后发货状态
        if apply.ORAstate == OrderRefundORAstate.goods_money.value and apply.ORAstatus == ApplyStatus.agree.value:
            order_refund_instance = self._get_order_refund({'ORAid': apply.ORAid})
            o.fill('order_refund', order_refund_instance)
            # 已发货
            time_now = datetime.now()
            if detail and order_refund_instance.ORstatus > OrderRefundOrstatus.wait_send.value:
                if (not order_refund_instance.ORlogisticData or (
                        time_now - order_refund_instance.updatetime).total_seconds() > 6 * 3600) \
                        and order_refund_instance.ORlogisticLostResult != 3:  # 没有data信息或超过6小时 并且状态不是已签收
                    l = Logistics()
                    current_app.logger.info('正在查询售后物流信息')
                    response = l.get_logistic(order_refund_instance.ORlogisticsn,
                                              order_refund_instance.ORlogisticCompany)
                    if response:
                        # 插入数据库
                        with db.auto_commit():
                            code = response.get('status')
                            if code == '0':

                                result = response.get('result')
                                order_refund_instance.update({
                                    'ORlogisticSignStatus': int(result.get('deliverystatus')),
                                    'ORlogisticData': json.dumps(result),
                                    'ORlogisticLostResult': json.dumps(result.get('list')[0])
                                })
                                db.session.add(order_refund_instance)
                                #
                            else:
                                current_app.logger.error('获取售后物流异常')
                                OrderLogisticsDict = {
                                    'ORlogisticSignStatus': -1,
                                    'ORlogisticData': json.dumps(response),  # 结果原字符串
                                    'ORlogisticLostResult': '{}'
                                }
                                order_refund_instance.update(OrderLogisticsDict)
                                db.session.add(order_refund_instance)
                try:
                    order_refund_instance.ORlogisticLostResult = json.loads(
                        order_refund_instance.ORlogisticLostResult)
                    order_refund_instance.ORlogisticData = json.loads(order_refund_instance.ORlogisticData)
                except Exception:
                    current_app.logger.error('售后物流出错')

    def _update_stock(self, old_new, product=None, sku=None, **kwargs):
        if not old_new:
            return
        skuid = kwargs.get('skuid')
        if skuid:
            sku = ProductSku.query.filter(ProductSku.SKUid == skuid).first()
            product = Products.query.filter(Products.PRid == sku.PRid).first()
        current_app.logger.info(product.PRstocks)
        product.PRstocks = product.PRstocks + old_new
        sku.SKUstock += sku.SKUstock + old_new
        current_app.logger.info(product.PRstocks)
        if product.PRstocks < 0:
            raise StatusError('商品库存不足')
        if product.PRstocks and product.PRstatus == ProductStatus.sell_out.value:
            product.PRstatus = ProductStatus.usual.value
        if product.PRstocks == 0:
            product.PRstatus = ProductStatus.sell_out.value
        db.session.add(sku)
        db.session.add(product)

