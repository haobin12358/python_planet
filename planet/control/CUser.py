import json
import random
import time
import datetime
import uuid
from decimal import Decimal

from alipay import AliPay
from flask import request

from planet.common.params_validates import parameter_required
from planet.common.error_response import ParamsError, SystemError, TokenError, TimeError
from planet.common.success_response import Success
from planet.common.base_service import get_session
from planet.common.token_handler import token_required, is_tourist, usid_to_token
from planet.common.Inforsend import SendSMS
from planet.config.enums import PayType, Client, OrderFrom, OrderMainStatus, OrderPartStatus
from planet.config.secret import appid, mch_id, mch_key, wxpay_notify_url, alipay_appid, app_private_path, \
    alipay_public_key_path, alipay_notify
from planet.extensions.weixin import WeixinPay
from planet.models.user import User, UserLoginTime, UserCommission
from planet.models.identifyingcode import IdentifyingCode



class CUser:
    def login(self):
        """手机验证码登录"""
        data = parameter_required('usatelphone', '')
        ustelphone = data.get('ustelphone')
        uspassword = data.get('uspassword')

    def get_inforcode(self):
        """发送/校验验证码"""
        args = request.args.to_dict()
        print('get inforcode args: {0}'.format(args))
        Utel = args.get('ustelphone')

        # 拼接验证码字符串（6位）
        code = ""
        while len(code) < 6:
            import random
            item = random.randint(1, 9)
            code = code + str(item)

        # 获取当前时间，与上一次获取的时间进行比较，小于60秒的获取直接报错

        time_time = datetime.datetime.now()

        # 根据电话号码获取时间
        session, status = get_session()
        if not status:
            raise SystemError(u'数据库连接失败')

        time_up = session.query(IdentifyingCode).filter(IdentifyingCode.ICtelphone == Utel).first_()
        print("this is time up %s", time_up)

        if time_up:
            delta = time_time - time_up
            if delta.seconds < 60:
                raise TimeError(u"验证码已发送")

        newidcode = IdentifyingCode
        newidcode.ICtelphone, newidcode.ICcode, newidcode.ICid = Utel, code, str(uuid.uuid1())

        params = {"code": code}
        response_send_message = SendSMS(Utel, params)

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