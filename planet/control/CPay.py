# -*- coding: utf-8 -*-
import json
import re
import uuid
from datetime import datetime
from decimal import Decimal

from flask import request, current_app

from planet.common.params_validates import parameter_required
from planet.common.error_response import ParamsError, SystemError, ApiError, StatusError
from planet.common.success_response import Success
from planet.common.token_handler import token_required
from planet.config.cfgsetting import ConfigSettings
from planet.config.enums import PayType, Client, OrderMainStatus, OrderFrom, UserCommissionType
from planet.control.BaseControl import Commsion
from planet.extensions.register_ext import alipay, wx_pay
from planet.extensions.weixin.pay import WeixinPayError
from planet.models import User, UserCommission, ProductBrand, ProductItems, Items
from planet.models import OrderMain, OrderPart, OrderPay, FreshManJoinFlow
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
        data = parameter_required(('omid', ))
        omid = data.get('omid')
        usid = request.user.id
        try:
            omclient = data.get('omclient', Client.wechat.value)  # 测试
            if omclient != 'test':
                omclient = int(data.get('omclient', Client.wechat.value))  # 客户端(app或者微信)
                Client(omclient)
            opaytype = int(data.get('opaytype', PayType.wechat_pay.value))  # 付款方式
            PayType(opaytype)

        except ValueError as e:
            raise e
        except Exception as e:
            raise ParamsError('客户端或支付方式类型错误')
        with self.strade.auto_commit() as s:
            session_list = []
            opayno = self.wx_pay.nonce_str
            order_main = s.query(OrderMain).filter_by_({
                'OMid': omid, 'USid': usid, 'OMstatus': OrderMainStatus.wait_pay.value
            }).first_('不存在的订单')
            # 原支付流水删除
            s.query(OrderPay).filter_by({'OPayno': order_main.OPayno}).delete_()
            # 更改订单支付编号
            order_main.OPayno = opayno
            session_list.append(order_main)
            # 新建支付流水
            order_pay_instance = OrderPay.create({
                'OPayid': str(uuid.uuid4()),
                'OPayno': opayno,
                'OPayType': opaytype,
                'OPayMount': order_main.OMtrueMount
            })
            # 付款时候的body信息
            order_parts = s.query(OrderPart).filter_by_({'OMid': omid}).all()
            body = ''.join([getattr(x, 'PRtitle', '') for x in order_parts])
            session_list.append(order_pay_instance)
            s.add_all(session_list)
        user = User.query.filter(User.USid == order_main.USid).first()
        pay_args = self._pay_detail(omclient, opaytype, opayno, float(order_main.OMtrueMount), body, openid=user.USopenid1 or user.USopenid2)
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
        if not(success and data["trade_status"] in ("TRADE_SUCCESS", "TRADE_FINISHED")):
            return
        print("trade succeed")
        out_trade_no = data.get('out_trade_no')
        # 交易成功
        with self.strade.auto_commit() as s:
            s_list = []
            # 更改付款流水
            order_pay_instance = s.query(OrderPay).filter_by({'OPayno': out_trade_no}).first_('异常支付')
            order_pay_instance.OPaytime = data.get('gmt_payment')
            order_pay_instance.OPaysn = data.get('trade_no')  # 支付宝交易凭证号
            order_pay_instance.OPayJson = json.dumps(data)
            s_list.append(order_pay_instance)
            # 更改主单
            order_mains = s.query(OrderMain).filter_by({'OPayno': out_trade_no}).all()
            for order_main in order_mains:
                is_upgrade_gift = bool(s.query(OrderPart).firter(
                        OrderMain.OMid == OrderPart.OMid,
                        ProductBrand.PRid == OrderPart.PRid,
                        ProductItems.ITid == Items.ITid,
                        Items.ITname == '开店大礼包').all())
                if not is_upgrade_gift:
                    order_main.update({
                        'OMstatus': OrderMainStatus.wait_send.value
                    })
                    s_list.append(order_main)
                    # 添加佣金记录
                    commion_instance_list = self._insert_usercommision(s, order_main)
                    s_list.extend(commion_instance_list)
                else:
                    # 如果是开店大礼包，则直接订单完成
                    order_main.update({
                        'OMstatus': OrderMainStatus.ready.value
                    })
                    s_list.append(order_main)
            s.add_all(s_list)
        return 'success'

    def wechat_notify(self):
        """微信支付回调"""
        # 待测试
        data = self.wx_pay.to_dict(request.data)
        if not self.wx_pay.check(data):
            return self.wx_pay.reply(u"签名验证失败", False)
        out_trade_no = data.get('out_trade_no')
        with self.strade.auto_commit() as s:
            s_list = []
            # 更改付款流水
            order_pay_instance = s.query(OrderPay).filter_by_({'OPayno': out_trade_no}).first_()
            order_pay_instance.OPaytime = data.get('time_end')
            order_pay_instance.OPaysn = data.get('transaction_id')  # 微信支付订单号
            order_pay_instance.OPayJson = json.dumps(data)
            # 更改主单
            order_mains = s.query(OrderMain).filter_by_({'OPayno': out_trade_no}).all()
            for order_main in order_mains:
                order_main.update({
                    'OMstatus': OrderMainStatus.wait_send.value
                })
                s_list.append(order_main)
                # 添加佣金记录
                commion_instance_list = self._insert_usercommision(s, order_main)
                s_list.extend(commion_instance_list)
            s.add_all(s_list)
        return self.wx_pay.reply("OK", True).decode()

    def _insert_usercommision(self, s, order_main):
        """写入佣金流水表"""
        s_list = []
        # up1 = order_main.UPperid
        # up2 = order_main.UPperid2
        omid = order_main.OMid
        # if not up1:
        #     return []
        user = s.query(User).filter_by_({'USid': order_main.USid}).first()  # 订单用户
        current_app.logger.info(dict(user))
        cfg = ConfigSettings()
        user_level1commision = user.USCommission1 or cfg.get_item('commission', 'level1commision')
        user_level2commision = user.USCommission2 or cfg.get_item('commission', 'level2commision')
        planetcommision = cfg.get_item('integralbase', 'integral')  # 平台佣金比例
        order_parts = s.query(OrderPart).filter_by_({
            'OMid': omid
        }).all()
        #
        if order_main.OMfrom == OrderFrom.trial_commodity.value:  # 试用
            UCtype = UserCommissionType.deposit.value  # 押金
            UCendTime = datetime.now()   # todo 如何定义时间??
        else:
            UCtype = None
            UCendTime = None
        for order_part in order_parts:
            up1 = order_part.UPperid
            up2 = order_part.UPperid2
            if not up1:
                continue
            level1commision = order_part.USCommission1 or user_level1commision
            user_commision_dict = {
                'UCid': str(uuid.uuid1()),
                'OMid': omid,
                'OPid': order_part.OPid,
                'UCcommission': Decimal(level1commision) * Decimal(order_part.OPsubTrueTotal) /  Decimal(100),
                'USid': up1,
                'UCtype': UCtype,
                'PRtitle': order_part.PRtitle,
                'SKUpic': order_part.SKUpic,
                'UCendTime': UCendTime

            }
            s_list.append(UserCommission.create(user_commision_dict))
            if not up2:
                continue
            level2commision = order_part.USCommission2 or user_level2commision
            users_commision_dict = {
                'UCid': str(uuid.uuid1()),
                'OMid': omid,
                'OPid': order_part.OPid,
                'UCcommission': Decimal(level2commision) * Decimal(order_main.OMtrueMount) / Decimal(100),
                'USid': up2,
                'UCtype': UCtype,
                'PRtitle': order_part.PRtitle,
                'SKUpic': order_part.SKUpic,
                'UCendTime': UCendTime
            }
            s_list.append(UserCommission.create(users_commision_dict))

        # 新人活动订单
        if order_main.OMfrom == OrderFrom.fresh_man.value:
            fresh_man_join_flow = FreshManJoinFlow.query.filter(
                FreshManJoinFlow.isdelete == False,
                FreshManJoinFlow.OMid == order_main.OMid,
            ).first()
            if fresh_man_join_flow and fresh_man_join_flow.UPid:
                pass
                # todo 新人首单奖励分发

        return s_list

    def test_pay(self, out_trade_no=1, mount_price=1):
        order_string = self.alipay.api_alipay_trade_page_pay(
            out_trade_no=out_trade_no,
            total_amount=mount_price,
            subject='testestestestestestestestsetestsetsetest',
        )
        return order_string

    def _pay_detail(self, omclient, opaytype, opayno, mount_price, body, openid='openid'):
        body = re.sub("[\s+\.\!\/_,$%^*(+\"\'\-_]+|[+——！，。？、~@#￥%……&*（）]+", '', body)
        mount_price = 0.01
        current_app.logger.info('openid is {}'.format(openid))
        ####
        # 一种测试的付款方式, 使用支付宝网页支付
        if omclient == 'test':
            return self.test_pay(out_trade_no=opayno, mount_price=mount_price)
        ####
        # 微信支付的单位是'分', 支付宝使用的单位是'元'
        if opaytype == PayType.wechat_pay.value:
            try:
                body = body[:16] + '...'
                current_app.logger.info('body is {}'.format(body))
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
        else:
            raise SystemError('请选用其他支付方式')
        return raw

    def _pay_to_user(self, opaytype):
        """
        向用户提现
        :return:
        """
        pass



