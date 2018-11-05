# -*- coding: utf-8 -*-
import json
import random
import time
import uuid
from decimal import Decimal

from alipay import AliPay
from flask import request

from planet.common.params_validates import parameter_required
from planet.common.error_response import ParamsError, SystemError
from planet.common.success_response import Success
from planet.common.token_handler import token_required
from planet.config.enums import PayType, Client, OrderMainStatus
from planet.config.secret import appid, mch_id, mch_key, wxpay_notify_url, alipay_appid, app_private_path, \
    alipay_public_key_path, alipay_notify
from planet.extensions.weixin import WeixinPay
from planet.models.trade import OrderMain, OrderPart, OrderPay
from planet.service.STrade import STrade


class CPay():
    def __init__(self):
        self.strade = STrade()

    @token_required
    def pay(self):
        """订单发起支付"""
        data = parameter_required(('omid', ))
        omid = data.get('omid')
        try:
            omclient = int(data.get('omclient', Client.wechat.value))  # 客户端(app或者微信)
            opaytype = int(data.get('opaytype', PayType.wechat_pay.value))  # 付款方式
            PayType(opaytype)
            Client(omclient)
        except ValueError as e:
            raise e
        except Exception as e:
            raise ParamsError('客户端或支付方式类型错误')
        with self.strade.auto_commit() as s:
            opayno = self.wx_pay.nonce_str
            order_main = s.query(OrderMain).filter_by_({'OMid': omid}).first_('不存在的订单')
            # 原支付流水删除
            s.query(OrderPay).filter_by_({'OPayno': order_main.OPayno}).delete_()
            # 更改订单支付编号
            order_main.OPayno = opayno
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
            s.add(order_pay_instance)
        pay_args = self._pay_detail(omclient, opaytype, opayno, float(order_main.OMtrueMount), body)
        response = {
            'pay_type': PayType(opaytype).name,
            'opaytype': opaytype,
            'args': pay_args
        }
        return Success('生成付款参数成功', response)

    def alipay_notify(self):
        """异步通知, 文档 https://docs.open.alipay.com/203/105286/"""
        # 待测试
        data = request.json
        signature = data.pop("sign")
        success = self.alipay.verify(data, signature)
        if not(success and data["trade_status"] in ("TRADE_SUCCESS", "TRADE_FINISHED")):
            return
        print("trade succeed")
        out_trade_no = data.get('out_trade_no')
        # 交易成功
        with self.strade.auto_commit() as s:
            # 更改付款流水
            order_pay_instance = s.query(OrderPay).filter_by_({'OPayno': out_trade_no}).first_()
            order_pay_instance.OPaytime = data.get('gmt_payment')
            order_pay_instance.OPaysn = data.get('trade_no')  # 支付宝交易凭证号
            order_pay_instance.OPayJson = json.dumps(data)
            # 更改主单
            s.query(OrderMain).filter_by_({'OPayno': out_trade_no}).update({
                'OMstatus': OrderMainStatus.wait_send.value
            })
        return 'success'

    def wechat_notify(self):
        """微信支付回调"""
        # 待测试
        data = self.pay.to_dict(request.data)
        if not self.pay.check(data):
            return self.pay.reply(u"签名验证失败", False)
        out_trade_no = data.get('out_trade_no')
        with self.strade.auto_commit() as s:
            # 更改付款流水
            order_pay_instance = s.query(OrderPay).filter_by_({'OPayno': out_trade_no}).first_()
            order_pay_instance.OPaytime = data.get('time_end')
            order_pay_instance.OPaysn = data.get('transaction_id')  # 微信支付订单号
            order_pay_instance.OPayJson = json.dumps(data)
            # 更改主单
            s.query(OrderMain).filter_by_({'OPayno': out_trade_no}).update({
                'OMstatus': OrderMainStatus.wait_send.value
            })
            return self.pay.reply("OK", True)

    def _pay_detail(self, omclient, opaytype, opayno, mount_price, body, openid='openid'):
        if opaytype == PayType.wechat_pay.value:
            body = body[:110] + '...'
            wechat_pay_dict = dict(
                body=body,
                out_trade_no=opayno,
                total_fee=int(mount_price * 100), attach='attach',
                spbill_create_ip=request.remote_addr
            )
            if omclient == Client.wechat.value:  # 微信客户端
                wechat_pay_dict.update(dict(trade_type="JSAPI", openid=openid))
                raw = self.wx_pay.jsapi(**wechat_pay_dict)
            else:
                wechat_pay_dict.update(dict(trade_type="APP"))
                raw = self.wx_pay.unified_order(**wechat_pay_dict)
        elif opaytype == PayType.alipay.value:
            if omclient == Client.wechat.value:
                raise SystemError('请选用其他支付方式')
            else:
                raw = self.alipay.api_alipay_trade_app_pay(
                    out_trade_no=opayno,
                    total_amount=mount_price,
                    subject=body[:200] + '...',
                )
        else:
            raise SystemError('请选用其他支付方式')
        return raw

    @property
    def wx_pay(self):
        return WeixinPay(appid, mch_id, mch_key, wxpay_notify_url)  # 后两个参数可选

    @property
    def alipay(self):
        return AliPay(
            appid=alipay_appid,
            app_notify_url=alipay_notify,  # 默认回调url
            app_private_key_string=open(app_private_path).read(),
            alipay_public_key_string=open(alipay_public_key_path).read(),
            sign_type="RSA",  # RSA 或者 RSA2
        )

