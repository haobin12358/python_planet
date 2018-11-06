import json
import random
import time
import uuid
from decimal import Decimal

from alipay import AliPay
from flask import request

from planet.common.params_validates import parameter_required
from planet.common.error_response import ParamsError, SystemError, TokenError
from planet.common.success_response import Success
from planet.common.token_handler import token_required, is_tourist
from planet.config.enums import PayType, Client, OrderFrom, OrderMainStatus, OrderPartStatus
from planet.config.secret import appid, mch_id, mch_key, wxpay_notify_url, alipay_appid, app_private_path, \
    alipay_public_key_path, alipay_notify
from planet.extensions.weixin import WeixinPay
from planet.models import ProductSku, Products, ProductBrand
from planet.models.trade import OrderMain, OrderPart, OrderPay, Carts
from planet.service.STrade import STrade


class CUser:
    def login(self):
        data = parameter_required('usatelphone', '')
        ustelphone = data.get('ustelphone')
        uspassword = data.get('uspassword')

    """发送/校验验证码"""

    @token_required
    def get_inforcode(self):
        if is_tourist():
            raise TokenError

        user = self.suser.get_user_by_user_id(request.user.id)
        if not user:
            return SystemError

        Utel = user.USphone
        # 拼接验证码字符串（6位）
        code = ""
        while len(code) < 6:
            import random
            item = random.randint(1, 9)
            code = code + str(item)

        # 获取当前时间，与上一次获取的时间进行比较，小于60秒的获取直接报错
        import datetime
        from planet.config.timeformat import format_for_db
        time_time = datetime.datetime.now()
        time_str = datetime.datetime.strftime(time_time, format_for_db)

        # 根据电话号码获取时间
        time_up = self.smycenter.get_uptime_by_utel(Utel)
        logger.debug("this is time up %s", time_up)

        if time_up:
            time_up_time = datetime.datetime.strptime(time_up.ICtime, format_for_db)
            delta = time_time - time_up_time
            if delta.seconds < 60:
                return import_status("ERROR_MESSAGE_GET_CODE_FAST", "WEIDIAN_ERROR", "ERROR_CODE_GET_CODE_FAST")

        new_inforcode = self.smycenter.add_inforcode(Utel, code, time_str)

        logger.debug("this is new inforcode %s ", new_inforcode)

        if not new_inforcode:
            return SYSTEM_ERROR
        from WeiDian.config.Inforcode import SignName, TemplateCode
        from WeiDian.common.Inforsend import send_sms
        params = '{\"code\":\"' + code + '\",\"product\":\"etech\"}'

        # params = u'{"name":"wqb","code":"12345678","address":"bz","phone":"13000000000"}'
        __business_id = uuid.uuid1()
        response_send_message = send_sms(__business_id, Utel, SignName, TemplateCode, params)

        response_send_message = json.loads(response_send_message)
        logger.debug("this is response %s", response_send_message)

        if response_send_message["Code"] == "OK":
            status = 200
        else:
            status = 405
        # 手机号中四位替换为星号
        # response_ok = {"usphone": Utel[:3] + '****' + Utel[-4: ]}
        response_ok = {"usphone": Utel}
        response_ok["status"] = status
        response_ok["messages"] = response_send_message["Message"]

        return response_ok