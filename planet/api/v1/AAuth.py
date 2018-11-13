# -*- coding: utf-8 -*-
from flask import request, jsonify
from alipay import AliPay

from planet.common.base_resource import Resource
from planet.common.token_handler import usid_to_token


class AAuthTest(Resource):
    """临时登录"""
    def post(self):
        # data = request.json
        # usid = data.get('usid')
        data = request.json or {}
        usid = 'usid1'
        model = data.get('model', 'User')
        token = usid_to_token(usid, data.get('user', model))
        return token


class APayTest(Resource):
    def __init__(self):
        pass

    def get(self):
        """
        https://docs.open.alipay.com/204/105297/
        """
        # raw = self.alipay.api_alipay_trade_app_pay(
        #     out_trade_no="20161112",
        #     total_amount=0.01,
        #     subject='app',
        #     notify_url="https://example.com/notify"  # 可选, 不填则使用默认notify url
        # )
        raw = self.alipay.api_alipay_trade_app_pay(
            out_trade_no="20181112",
            total_amount=0.01,
            subject='手机',
            notify_url="https://example.com/notify"  # 可选, 不填则使用默认notify url
        )
        data = {'data': raw}
        return jsonify(data)

    def post(self):
        """回调"""
        data = request.json
        signature = data.pop("sign")
        success = self.alipay.verify(data, signature)
        if success and data["trade_status"] in ("TRADE_SUCCESS", "TRADE_FINISHED"):
            print("trade succeed")
        return success


    @property
    def alipay(self):
        return AliPay(
            appid="2016091900546396",
            app_notify_url='https://www.qup.com',  # 默认回调url
            app_private_key_string=self.app_private_key_string,
            # 支付宝的公钥，验证支付宝回传消息使用，不是你自己的公钥,
            alipay_public_key_string=self.alipay_public_key_string,
            sign_type="RSA2",  # RSA 或者 RSA2
            # debug=False  # 默认False
        )


    @property
    def app_private_key_string(self):
        return open('/home/wukt/app_private_key.pem').read()

    @property
    def alipay_public_key_string(self):
        return open('/home/wukt/public.pem').read()

    @property
    def wechat_pay(self):
        pass