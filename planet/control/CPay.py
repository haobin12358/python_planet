# -*- coding: utf-8 -*-
import json
import random
import re
import time
import uuid
from datetime import datetime, timedelta
from decimal import Decimal
from functools import reduce
from operator import mul

from flask import request, current_app

from planet.common.params_validates import parameter_required
from planet.common.error_response import ParamsError, SystemError, ApiError, StatusError
from planet.common.success_response import Success
from planet.common.token_handler import token_required
from planet.config.cfgsetting import ConfigSettings
from planet.config.enums import PayType, Client, OrderMainStatus, OrderFrom, UserCommissionType, OMlogisticTypeEnum, \
    LogisticsSignStatus, UserIdentityStatus, UserCommissionStatus, ApplyFrom
from planet.extensions.register_ext import alipay, wx_pay, db
from planet.extensions.weixin.pay import WeixinPayError
from planet.models import User, UserCommission, ProductBrand, ProductItems, Items, TrialCommodity, OrderLogistics, \
    Products, Supplizer
from planet.models import OrderMain, OrderPart, OrderPay, FreshManJoinFlow, ProductSku
from planet.models.commision import Commision
from planet.service.STrade import STrade
from planet.service.SUser import SUser


class CPay():
    def __init__(self):
        self.strade = STrade()
        self.suser = SUser()
        self.alipay = alipay
        self.wx_pay = wx_pay

    @token_required
    def pay(self):
        """订单发起支付"""
        data = parameter_required(('omid',))
        omid = data.get('omid')
        usid = request.user.id
        try:
            omclient = int(data.get('omclient', Client.wechat.value))  # 客户端(app或者微信)
            Client(omclient)
            opaytype = int(data.get('opaytype', PayType.wechat_pay.value))  # 付款方式
            PayType(opaytype)
        except ValueError as e:
            raise e
        except Exception as e:
            raise ParamsError('客户端或支付方式类型错误')
        from planet.control.CUser import CUser
        cuser = CUser()
        with db.auto_commit():
            opayno = self.wx_pay.nonce_str
            order_main = OrderMain.query.filter_by_({
                'OMid': omid, 'USid': usid, 'OMstatus': OrderMainStatus.wait_pay.value
            }).first_('不存在的订单')
            # 原支付流水删除
            OrderPay.query.filter_by({'OPayno': order_main.OPayno}).delete_()
            # 更改订单支付编号
            order_main.OPayno = opayno
            # 判断订单是否是开店大礼包
            # 是否是开店大礼包
            if order_main.OMlogisticType == OMlogisticTypeEnum.online.value:
                cuser = CUser()
                cuser._check_gift_order('重复购买开店大礼包')
            db.session.add(order_main)
            # 新建支付流水
            order_pay_instance = OrderPay.create({
                'OPayid': str(uuid.uuid1()),
                'OPayno': opayno,
                'OPayType': opaytype,
                'OPayMount': order_main.OMtrueMount
            })
            # 付款时候的body信息
            order_parts = OrderPart.query.filter_by_({'OMid': omid}).all()
            body = ''.join([getattr(x, 'PRtitle', '') for x in order_parts])
            db.session.add(order_pay_instance)
        user = User.query.filter(User.USid == order_main.USid).first()
        pay_args = self._pay_detail(omclient, opaytype, opayno, float(order_main.OMtrueMount), body,
                                    openid=user.USopenid1 or user.USopenid2)
        response = {
            'pay_type': PayType(opaytype).name,
            'opaytype': opaytype,
            'args': pay_args
        }
        return Success('生成付款参数成功', response)

    def alipay_notify(self):
        """异步通知, 文档 https://docs.open.alipay.com/203/105286/"""
        # 待测试
        data = request.form.to_dict()
        signature = data.pop("sign")
        success = self.alipay.verify(data, signature)
        if not (success and data["trade_status"] in ("TRADE_SUCCESS", "TRADE_FINISHED")):
            return
        print("trade succeed")
        out_trade_no = data.get('out_trade_no')
        # 交易成功
        with self.strade.auto_commit() as s:
            # 更改付款流水
            order_pay_instance = OrderPay.query.filter_by_({'OPayno': out_trade_no}).first_()
            order_pay_instance.OPaytime = data.get('gmt_payment')
            order_pay_instance.OPaysn = data.get('trade_no')  # 支付宝交易凭证号
            order_pay_instance.OPayJson = json.dumps(data)
            # 更改主单
            order_mains = OrderMain.query.filter_by_({'OPayno': out_trade_no}).all()
            for order_main in order_mains:
                order_main.update({
                    'OMstatus': OrderMainStatus.wait_send.value
                })
                db.session.add(order_main)
                # 添加佣金记录
                current_app.logger.info('支付宝付款成功')
                self._insert_usercommision(order_main)
        return 'success'

    def wechat_notify(self):
        """微信支付回调"""
        data = self.wx_pay.to_dict(request.data)
        if not self.wx_pay.check(data):
            return self.wx_pay.reply(u"签名验证失败", False)
        out_trade_no = data.get('out_trade_no')
        with db.auto_commit():
            # 更改付款流水
            order_pay_instance = OrderPay.query.filter_by_({'OPayno': out_trade_no}).first_()
            order_pay_instance.OPaytime = data.get('time_end')
            order_pay_instance.OPaysn = data.get('transaction_id')  # 微信支付订单号
            order_pay_instance.OPayJson = json.dumps(data)
            # 更改主单
            order_mains = OrderMain.query.filter_by_({'OPayno': out_trade_no}).all()
            for order_main in order_mains:
                order_main.update({
                    'OMstatus': OrderMainStatus.wait_send.value
                })
                # 添加佣金记录
                current_app.logger.info('微信支付成功')
                self._insert_usercommision(order_main)
        return self.wx_pay.reply("OK", True).decode()

    def _insert_usercommision(self, order_main):
        """写入佣金流水表"""
        omid = order_main.OMid
        user = User.query.filter_by_({'USid': order_main.USid}).first()  # 订单用户
        try:
            current_app.logger.info(
                '当前付款人: {}, 状态: {}  '.format(user.USname, UserIdentityStatus(user.USlevel).zh_value))
        except Exception:
            pass
        commision = Commision.query.filter(Commision.isdelete == False).first()
        order_parts = OrderPart.query.filter_by_({
            'OMid': omid
        }).all()
        UCstatus = None
        UCendTime = None
        is_trial_commodity = order_main.OMfrom == OrderFrom.trial_commodity.value
        for order_part in order_parts:
            # 是否是新人大礼包
            prid = order_part.PRid
            if self._check_upgrade_gift((prid, )):
                current_app.logger.info('开店礼包不需要佣金')
                user.USlevel = UserIdentityStatus.toapply.value
                continue
            if is_trial_commodity:
                trialcommodity = TrialCommodity.query.filter_by(TCid=order_parts[0]['PRid']).first()
                user_commision_dict = {
                    'UCid': str(uuid.uuid1()),
                    'OMid': omid,
                    'OPid': order_part.OPid,
                    'UCcommission': order_main.OMtrueMount,
                    'USid': user.USid,
                    'UCtype': UserCommissionType.deposit.value,  # 类型是押金
                    'PRtitle': order_part.PRtitle,
                    'SKUpic': order_part.SKUpic,
                    'UCendTime': order_main.createtime + timedelta(days=trialcommodity.TCdeadline),
                    'UCstatus': UCstatus,
                    'FromUsid': order_main.USid
                }
                db.session.add(UserCommission.create(user_commision_dict))
                continue
            up1 = order_part.UPperid
            up2 = order_part.UPperid2
            up3 = order_part.UPperid3
            # 如果付款用户是代理商
            if UserIdentityStatus.agent.value == user.USlevel:
                up1, up2, up3 = user.USid, up1, up2  # 代理商自己也会有一部分佣金
            up1_user = User.query.filter(User.isdelete == False, User.USid == up1).first()
            up2_user = User.query.filter(User.isdelete == False, User.USid == up2).first()
            up3_user = User.query.filter(User.isdelete == False, User.USid == up3).first()
            self._caculate_commsion(user, up1_user, up2_user, up3_user, commision,
                                    order_part, is_act=bool(order_main.OMfrom>OrderFrom.product_info.value))
        # 新人活动订单
        if order_main.OMfrom == OrderFrom.fresh_man.value:
            fresh_man_join_flow = FreshManJoinFlow.query.filter(
                FreshManJoinFlow.isdelete == False,
                FreshManJoinFlow.OMid == order_main.OMid,
            ).first()
            if fresh_man_join_flow and fresh_man_join_flow.UPid:
                # 邀请人的新人首单
                up_order_main = OrderMain.query.filter(
                    OrderMain.isdelete == True,
                    OrderMain.USid == fresh_man_join_flow.UPid,
                    OrderMain.OMfrom == OrderFrom.fresh_man.value,
                    OrderMain.OMstatus > OrderMainStatus.wait_pay.value,
                ).first()
                if up_order_main:
                    reward = min(order_main.OMtrueMount, up_order_main.OMtrueMount)
                    user_commision_dict = {
                        'UCid': str(uuid.uuid1()),
                        'OMid': omid,
                        'UCcommission': reward,
                        'USid': fresh_man_join_flow.UPid,
                        'UCtype': UserCommissionType.fresh_man.value,
                        'UCendTime': UCendTime
                    }
                    db.session.add(UserCommission.create(user_commision_dict))
        # 线上发货
        if order_main.OMlogisticType == OMlogisticTypeEnum.online.value:
            order_main.OMstatus = OrderMainStatus.ready.value
            db.session.add(order_main)
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
            db.session.add(orderlogistics)

    def _caculate_commsion(self, user, up1, up2, up3, commision, order_part, is_act=False):
        """计算各级佣金"""
        # 活动佣金即时到账
        suid = order_part.PRcreateId
        if is_act:
            current_app.logger.info('活动订单和押金即时到账')
            UCstatus = UserCommissionStatus.in_account.value
        else:
            UCstatus = None
        default_level1commision, default_level2commision, default_level3commision, default_planetcommision = json.loads(
            commision.Levelcommision
        )
        reduce_ratio = json.loads(commision.ReduceRatio)
        increase_ratio = json.loads(commision.IncreaseRatio)
        # 基础佣金比
        user_level1commision = Decimal(
            str(self._current_commission(getattr(order_part, 'USCommission1', ''), default_level1commision))
        )
        user_level2commision = Decimal(
            str(self._current_commission(getattr(order_part, 'USCommission2', ''), default_level2commision))
        )
        user_level3commision = Decimal(
            str(self._current_commission(getattr(order_part, 'USCommission3', ''), default_level3commision))
        )
        # 平台 + 用户 抽成: 获取成功比例, 依次查找订单--> sku --> 系统默认
        planet_and_user_rate = Decimal(str(order_part.SkudevideRate or 0))

        if not planet_and_user_rate:
            sku = ProductSku.query.filter(ProductSku.SKUid == OrderPart.SKUid).first()
            if sku:
                planet_and_user_rate = Decimal(str(sku.SkudevideRate or 0))
        if not planet_and_user_rate:
            planet_and_user_rate = default_planetcommision
        planet_and_user_rate = Decimal(planet_and_user_rate) / 100
        # 平台固定抽成
        planet_rate = Decimal(default_planetcommision) / 100
        planet_commision = order_part.OPsubTotal * planet_rate   # 平台获得, 是总价的的百分比
        user_commision = order_part.OPsubTotal * planet_and_user_rate - planet_commision  # 用户获得, 是总价 - 平台获得
        # user_rate = planet_and_user_rate - planet_rate  # 用户的的比例
        # 用户佣金
        commision_for_supplizer = order_part.OPsubTotal * (Decimal('1') - planet_and_user_rate)   #  给供应商的钱   总价 * ( 1 - 让利 )
        commision_for_supplizer = self.get_two_float(commision_for_supplizer)

        # 正常应该获得佣金
        up1_base = up2_base = up3_base = 0
        if up1 and up1.USlevel > 1:
            user_level1commision = self._current_commission(up1.USCommission1, user_level1commision) / 100  # 个人佣金比
            up1_base = user_commision * user_level1commision
            if up2 and up2.USlevel > 1:
                user_level2commision = self._current_commission(up2.USCommission2, user_level2commision) / 100  # 个人佣金比
                up2_base = user_commision * user_level2commision
                # 偏移
                up1_up2 = up1.CommisionLevel - up2.CommisionLevel
                up1_base, up2_base = self._caculate_offset(up1_up2, up1_base, up2_base, reduce_ratio, increase_ratio)
                if up3 and up3.USlevel > 1:
                    user_level3commision = self._current_commission(up3.USCommission3, user_level3commision) / 100  # 个人佣金比
                    up3_base = user_commision * user_level3commision
                    up2_up3 = Decimal(up2.CommisionLevel) - Decimal(up3.CommisionLevel)
                    up2_base, up3_base = self._caculate_offset(up2_up3, up2_base, up3_base, reduce_ratio,
                                                               increase_ratio)
        if up1_base:
            up1_base = self.get_two_float(up1_base)
            user_commision -= up1_base
            current_app.logger.info('一级获得佣金: {}'.format(up1_base))
            commision_account = UserCommission.create({
                'UCid': str(uuid.uuid1()),
                'OMid': order_part.OMid,
                'OPid': order_part.OPid,
                'UCcommission': up1_base,
                'USid': up1.USid,
                'PRtitle': order_part.PRtitle,
                'SKUpic': order_part.SKUpic,
                'UCstatus': UCstatus,
                'FromUsid': user.USid
            })
            db.session.add(commision_account)
        if up2_base:
            up2_base = self.get_two_float(up2_base)
            user_commision -= up2_base
            current_app.logger.info('二级获得佣金: {}'.format(up2_base))
            commision_account = UserCommission.create({
                'UCid': str(uuid.uuid1()),
                'OMid': order_part.OMid,
                'OPid': order_part.OPid,
                'UCcommission': up2_base,
                'USid': up2.USid,
                'PRtitle': order_part.PRtitle,
                'SKUpic': order_part.SKUpic,
                'UCstatus': UCstatus,
                'FromUsid': user.USid
            })
            db.session.add(commision_account)
        if up3_base:
            up3_base = self.get_two_float(up3_base)
            user_commision -= up3_base
            current_app.logger.info('三级获得佣金: {}'.format(up3_base))
            commision_account = UserCommission.create({
                'UCid': str(uuid.uuid1()),
                'OMid': order_part.OMid,
                'OPid': order_part.OPid,
                'UCcommission': up3_base,
                'USid': up3.USid,
                'PRtitle': order_part.PRtitle,
                'SKUpic': order_part.SKUpic,
                'UCstatus': UCstatus,
                'FromUsid': user.USid
            })
            db.session.add(commision_account)
        planet_remain = user_commision + planet_commision
        # 优惠券计算
        order_coupon = order_part.order_coupon
        if order_coupon:
            if order_coupon.SUid:
                commision_for_supplizer -= (Decimal(order_part.OPsubTotal) - Decimal(order_part.OPsubTrueTotal))
            else:
                planet_remain -= (Decimal(order_part.OPsubTotal) - Decimal(order_part.OPsubTrueTotal))

        # 供应商获取佣金
        if suid:
            commision_account = UserCommission.create({
                'UCid': str(uuid.uuid1()),
                'OMid': order_part.OMid,
                'OPid': order_part.OPid,
                'UCcommission': commision_for_supplizer,
                'USid': suid,
                'CommisionFor': ApplyFrom.supplizer.value,
                'PRtitle': order_part.PRtitle,
                'SKUpic': order_part.SKUpic,
                'UCstatus': UCstatus,
                'FromUsid': user.USid
            })
            db.session.add(commision_account)
            current_app.logger.info('供应商获取佣金: {}'.format(commision_account.UCcommission))
        else:
            planet_remain += commision_for_supplizer
        # 平台剩余佣金
        commision_account = UserCommission.create({
            'UCid': str(uuid.uuid1()),
            'OMid': order_part.OMid,
            'OPid': order_part.OPid,
            'UCcommission': planet_remain,
            'USid': '0',
            'CommisionFor': ApplyFrom.platform.value,
            'PRtitle': order_part.PRtitle,
            'SKUpic': order_part.SKUpic,
            'UCstatus': UCstatus,
            'FromUsid': user.USid
        })
        db.session.add(commision_account)
        current_app.logger.info('平台获取: {}'.format(planet_remain))

    @token_required
    def get_preview_commision(self):
        # 活动佣金即时到账
        usid = request.user.id
        user = User.query.filter(User.isdelete == False, User.USid == usid).first()
        commision = Commision.query.filter(Commision.isdelete == False, ).order_by(Commision.createtime.desc()).first()
        level_commision = list(map(Decimal, json.loads(commision.Levelcommision)))
        ReduceRatio = list(map(Decimal, json.loads(commision.ReduceRatio)))
        IncreaseRatio = list(map(Decimal, json.loads(commision.IncreaseRatio)))
        level1_commision = self._current_commission(user.USCommission1, level_commision[0])
        default_planetcommision = level_commision[-1]
        up1, up2 = user, User.query.filter(User.isdelete == False, User.USid == user.USsupper1).first()
        order_price = Decimal()  # 订单实际价格
        info = parameter_required(('pbid', 'skus',))
        pbid = info.get('pbid')
        skus = info.get('skus')
        brand = ProductBrand.query.filter(ProductBrand.isdelete == False, ProductBrand.PBid == pbid).first()
        supplizer = Supplizer.query.filter(Supplizer.isdelete == False, Supplizer.SUid == brand.SUid).first()
        up1_bases = Decimal(0)
        for sku in skus:
            # 订单副单
            skuid = sku.get('skuid')
            opnum = int(sku.get('nums', 1))
            assert opnum > 0
            sku_instance = ProductSku.query.filter_by_({'SKUid': skuid}).first_('skuid: {}不存在'.format(skuid))
            small_total = Decimal(str(sku_instance.SKUprice)) * opnum
            # 订单价格计算
            order_price += small_total
            planet_and_user_rate = self._current_commission(sku_instance.SkudevideRate, getattr(supplizer, 'SUbaseRate', ''), default_planetcommision)
            planet_and_user_rate = Decimal(planet_and_user_rate) / 100
            # 平台固定抽成
            planet_rate = Decimal(default_planetcommision) / 100
            planet_commision = order_price * planet_rate  # 平台获得, 是总价的的百分比
            user_commision = order_price * planet_and_user_rate - planet_commision  # 用户获得, 是总价 - 平台获得
            # 正常应该获得佣金
            up1_base = up2_base = 0
            if up1 and up1.USlevel > 1:
                user_level1commision = self._current_commission(up1.USCommission1,
                                                                level1_commision) / 100  # 个人佣金比
                up1_base = user_commision * user_level1commision
                if up2 and up2.USlevel > 1:
                    user_level2commision = self._current_commission(up2.USCommission2,
                                                                    level1_commision) / 100  # 个人佣金比
                    up2_base = user_commision * user_level2commision
                    # 偏移
                    up1_up2 = up1.CommisionLevel - up2.CommisionLevel
                    up1_base, up2_base = self._caculate_offset(up1_up2, up1_base, up2_base, ReduceRatio,
                                                                   IncreaseRatio)
            up1_bases += up1_base
        return Success(data='%.2f' % up1_bases)

    def _caculate_offset(self, low_high, user_low_base, user_hign_base, reduce_ratio, increase_ratio):
        """计算偏移后的佣金"""
        if low_high <= 0:
            return user_low_base, user_hign_base
        low_ratio = Decimal()
        hign_ratio = Decimal('1')
        hign_comm_base_temp = user_hign_base
        for index in range(low_high):
            hign_comm_base_temp *= hign_ratio  # 本级的基础佣金比
            hign_ratio *= (1 - Decimal(reduce_ratio[index]) / 100)
            low_ratio += (hign_comm_base_temp * Decimal(increase_ratio[index]) / 100)
        return low_ratio + user_low_base, hign_ratio * user_hign_base

    def _pay_detail(self, omclient, opaytype, opayno, mount_price, body, openid='openid'):
        opaytype = int(opaytype)
        omclient = int(omclient)
        body = re.sub("[\s+\.\!\/_,$%^*(+\"\'\-_]+|[+——！，。？、~@#￥%……&*（）]+", '', body)
        mount_price = 0.01
        current_app.logger.info('openid is {}, out_trade_no is {} '.format(openid, opayno))
        # 微信支付的单位是'分', 支付宝使用的单位是'元'
        if opaytype == PayType.wechat_pay.value:
            try:
                body = body[:16] + '...'
                current_app.logger.info('body is {}, wechatpay'.format(body))
                wechat_pay_dict = {
                    'body': body,
                    'out_trade_no': opayno,
                    'total_fee': int(mount_price * 100),
                    'attach': 'attach',
                    'spbill_create_ip': request.remote_addr
                }

                if omclient == Client.wechat.value:  # 微信客户端
                    if not openid:
                        raise StatusError('用户未使用微信登录')
                    # wechat_pay_dict.update(dict(trade_type="JSAPI", openid=openid))
                    wechat_pay_dict.update({
                        'trade_type': 'JSAPI',
                        'openid': openid
                    })
                    raw = self.wx_pay.jsapi(**wechat_pay_dict)
                else:
                    wechat_pay_dict.update({
                        'trade_type': "APP"
                    })
                    raw = self.wx_pay.unified_order(**wechat_pay_dict)
            except WeixinPayError as e:
                raise SystemError('微信支付异常: {}'.format('.'.join(e.args)))

        elif opaytype == PayType.alipay.value:
            current_app.logger.info('body is {}, alipay'.format(body))
            if omclient == Client.wechat.value:
                raise SystemError('请选用其他支付方式')
            else:
                try:
                    raw = self.alipay.api_alipay_trade_app_pay(
                        out_trade_no=opayno,
                        total_amount=mount_price,
                        subject=body[:66] + '...',
                    )
                except Exception:
                    raise SystemError('支付宝参数异常')
        elif opaytype == PayType.test_pay.value:
            raw = self.alipay.api_alipay_trade_page_pay(
                out_trade_no=opayno,
                total_amount=mount_price,
                subject=body[10],
            )
            raw = 'https://openapi.alipaydev.com/gateway.do?' + raw
        else:
            raise SystemError('请选用其他支付方式')
        current_app.logger.info('pay response is {}'.format(raw))
        return raw

    def _pay_to_user(self, opaytype):
        """
        向用户提现
        :return:
        """
        pass

    @staticmethod
    def _generic_omno():
        """生成订单号"""
        return str(time.strftime('%Y%m%d%H%M%S', time.localtime(time.time()))) + \
               str(time.time()).replace('.', '')[-7:] + str(random.randint(1000, 9999))

    @staticmethod
    def _current_commission(*args):
        for comm in args:
            if comm is not None:
                return comm
        return 0

    def _check_upgrade_gift(self, prid_list):
         return Items.query.join(ProductItems, Items.ITid == ProductItems.ITid).filter(
            Items.isdelete == False,
            ProductItems.isdelete == False,
            Items.ITid == 'upgrade_product',
            ProductItems.PRid.in_(prid_list),
        ).first()

    @staticmethod
    def get_two_float(f_str, n=2):
        f_str = str(f_str)
        a, b, c = f_str.partition('.')
        c = (c+"0"*n)[:n]
        return Decimal(".".join([a, c]))

if __name__ == '__main__':
    res = CPay()
