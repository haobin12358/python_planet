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
from planet.common.default_head import GithubAvatarGenerator
from planet.common.Inforsend import SendSMS
from planet.common.request_handler import gennerc_log
from planet.models.user import User, UserLoginTime, UserCommission
from planet.service.SUser import SUser
from planet.models import IdentifyingCode


class CUser(SUser):
    @get_session
    def login(self):
        """手机验证码登录"""
        data = parameter_required('ustelphone', 'identifyingcode')
        ustelphone = data.get('ustelphone')
        identifyingcode = str(data.get('identifyingcode'))
        idcode = self.get_identifyingcode_by_ustelphone(ustelphone)
        if not idcode or str(idcode.ICcode) != identifyingcode:
            raise ParamsError('验证码有误')
        user = self.get_user_by_ustelphone(ustelphone)
        if not user:
            usid = str(uuid.uuid1())
            uslevel = 1
            default_head_path = GithubAvatarGenerator().save_avatar(usid)
            user = User.create({
                "USid": usid,
                "USname": '客官'+str(ustelphone)[:-4],
                "UStelphone": ustelphone,
                "USheader": default_head_path,
                "USintegral": 0,
                "USlevel": uslevel
            })
            self.session.add(user)
        else:
            usid = user.USid
            uslevel = user.USlevel
        userloggintime = UserLoginTime.create({
            "ULTid": str(uuid.uuid1()),
            "USid": usid,
            "USTip": request.remote_addr
        })
        self.session.add(userloggintime)
        token = usid_to_token(usid, model='User', level=uslevel)
        return Success('登录成功', data={'token': token})

    @get_session
    def get_inforcode(self):
        """发送/校验验证码"""
        args = request.args.to_dict()
        print('get inforcode args: {0}'.format(args))
        Utel = args.get('ustelphone')

        # 拼接验证码字符串（6位）
        code = ""
        while len(code) < 6:
            item = random.randint(1, 9)
            code = code + str(item)

        # 获取当前时间，与上一次获取的时间进行比较，小于60秒的获取直接报错

        time_time = datetime.datetime.now()

        # 根据电话号码获取时间
        time_up = self.get_identifyingcode_by_ustelphone(Utel)
        print("this is time up %s", time_up)

        if time_up:
            delta = time_time - time_up.createtime
            if delta.seconds < 60:
                raise TimeError("验证码已发送")

        newidcode = IdentifyingCode.create({
            "ICtelphone": Utel,
            "ICcode": code,
            "ICid": str(uuid.uuid1())
        })
        self.session.add(newidcode)

        params = {"code": code}
        response_send_message = SendSMS(Utel, params)

        if not response_send_message:
            raise SystemError('发送验证码失败')

        response = {
            'ustelphone': Utel
        }
        return Success('获取验证码成功', data=response)

    def wx_login(self):
        pass

    @get_session
    @token_required
    def get_user(self):
        user = self.get_user_by_id(request.user.id)
        gennerc_log('get user is {0}'.format(user))
        if not user:
            raise ParamsError('token error')


