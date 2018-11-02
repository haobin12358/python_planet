# -*- coding: utf-8 -*-
import time
import uuid
from decimal import Decimal

from alipay import AliPay
from flask import request

from planet.common.params_validates import parameter_required
from planet.common.error_response import ParamsError, SystemError
from planet.common.success_response import Success
from planet.common.token_handler import token_required
from planet.config.enums import PayType, Client, OrderFrom
from planet.config.secret import appid, mch_id, mch_key, wxpay_notify_url, alipay_appid
from planet.extensions.weixin import WeixinPay
from planet.models import ProductSku, Products, ProductBrand
from planet.models.trade import OrderMain, OrderPart, OrderPay, Carts
from planet.service.STrade import STrade


class COrder:
    def __init__(self):
        self.strade = STrade()

    @token_required
    def create(self):
        data = parameter_required(('info', 'omclient', 'omfrom', 'udid', 'opaytype'))
        usid = request.user.id
        udid = data.get('udid')  # todo udid 表示用户的地址信息
        opaytype = data.get('opaytype')
        try:
            omclient = int(data.get('omclient', 0))  # 下单设备
            omfrom = int(data.get('omfrom', 0))  # 商品来源
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
                        'SKUdetail': sku_instance.SKUdetail,
                        'PRtitle': product_instance.PRtitle,
                        'SKUprice': sku_instance.SKUprice,
                        'PRmainpic': product_instance.PRmainpic,
                        'OPnum': opnum,
                        'OPsubTotal': float(small_total),
                    }
                    order_part_instance = OrderPart.create(order_part_dict)
                    model_bean.append(order_part_instance)
                    # 订单价格计算
                    # 删除购物车
                    s.query(Carts).filter_by_({"USid": usid, "SKUid": skuid}).delete_()
                    # body 信息
                    body.add(product_instance.PRtitle)
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
                'OPayMount': mount_price
            }
            order_pay_instance = OrderPay.create(order_pay_dict)
            model_bean.append(order_pay_instance)
            # s.add_all(model_bean)
        # 生成支付信息
        body = ''.join(list(body))
        res = self._pay_detail(omclient, opaytype, opayno, mount_price, body)
        return Success('创建成功', data=res)

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
        return raw

    @staticmethod
    def _generic_omno():
        """生成订单号"""
        return str(time.strftime('%Y%m%d%H%M%S', time.localtime(time.time()))) +\
                 str(time.time()).replace('.', '')[-7:]

    @property
    def wx_pay(self):
        return WeixinPay(appid, mch_id, mch_key, wxpay_notify_url)  # 后两个参数可选

    @property
    def alipay(self):
        return AliPay(
            appid=alipay_appid,
            app_notify_url='https://www.qup.com',  # 默认回调url
            app_private_key_string=open('/home/wukt/app_private_key.pem').read(),
            alipay_public_key_string=open('/home/wukt/public.pem').read(),
            sign_type="RSA2",  # RSA 或者 RSA2
            # debug=False  # 默认False
        )
