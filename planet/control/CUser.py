import json
import random
import re
import time
import datetime
import uuid
from decimal import Decimal

from alipay import AliPay
from flask import request

from planet.common.params_validates import parameter_required
from planet.common.error_response import ParamsError, SystemError, TokenError, TimeError, NotFound
from planet.common.success_response import Success
from planet.common.base_service import get_session
from planet.common.token_handler import token_required, is_tourist, usid_to_token
from planet.common.default_head import GithubAvatarGenerator
from planet.common.Inforsend import SendSMS
from planet.common.request_handler import gennerc_log
from planet.models.user import User, UserLoginTime, UserCommission, UserAddress
from planet.service.SUser import SUser
from planet.models import IdentifyingCode
from planet.config.http_config import HTTP_HOST

class CUser(SUser):
    @get_session
    def login(self):
        """手机验证码登录"""
        data = parameter_required(('ustelphone', 'identifyingcode'))
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
    def login_test(self):
        """获取token"""
        data = parameter_required(('ustelphone',))
        ustelphone = data.get('ustelphone')

        user = self.get_user_by_ustelphone(ustelphone)
        if not user:
            usid = str(uuid.uuid1())
            uslevel = 1
            default_head_path = GithubAvatarGenerator().save_avatar(usid)
            user = User.create({
                "USid": usid,
                "USname": '客官' + str(ustelphone)[:-4],
                "UStelphone": ustelphone,
                "USheader": default_head_path,
                "USintegral": 0,
                "USlevel": uslevel
            })
            self.session.add(user)
        else:
            usid = user.USid
            uslevel = user.USlevel

        # 用户登录记录
        userloggintime = UserLoginTime.create({
            "ULTid": str(uuid.uuid1()),
            "USid": usid,
            "USTip": request.remote_addr
        })
        self.session.add(userloggintime)
        token = usid_to_token(usid, model='User', level=uslevel)
        print(token, type(token))
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
    def get_home(self):
        """获取个人主页信息"""
        user = self.get_user_by_id(request.user.id)
        gennerc_log('get user is {0}'.format(user))
        if not user:
            raise ParamsError('token error')
        # todo 插入 优惠券信息
        # user.add('优惠券')
        user.fields = ['USname', 'USintegral','USheader', 'USlevel', 'USqrcode', 'USgender']
        return Success('获取首页用户信息成功', data=user)

    @get_session
    @token_required
    def get_profile(self):
        """ 个人资料"""
        user = self.get_user_by_id(request.user.id)
        gennerc_log('get user is {0}'.format(user))
        if not user:
            raise ParamsError('token error')
        user.fields = ['USname', 'USbirthday', 'USheader', 'USlevel', 'USgender']
        return Success('获取个人资料信息成功', data=user)

    @get_session
    @token_required
    def get_safecenter(self):
        """安全中心"""
        user = self.get_user_by_id(request.user.id)
        gennerc_log('get user is {0}'.format(user))
        if not user:
            raise ParamsError('token error')
        user.fields = ['USname', 'USrealname', 'USheader', 'USlevel', 'USgender', 'USidentification', 'UStelphone']
        return Success('获取安全中心信息成功', data=user)

    @get_session
    @token_required
    def get_identifyinginfo(self):
        """获取个人身份证详情"""
        user = self.get_user_by_id(request.user.id)
        gennerc_log('get user is {0}'.format(user))
        if not user:
            raise ParamsError('token error')
        user.fields = ['USname', 'USrealname', 'USheader', 'USlevel', 'USgender', 'USidentification']
        usmedia = self.get_usermedia(user.USid)
        user.fill('usmedia', usmedia)
        return Success('获取身份证详情成功', data=user)

    @get_session
    @token_required
    def get_useraddress(self):
        """获取用户地址列表"""
        user = self.get_user_by_id(request.user.id)
        gennerc_log('get user is {0}'.format(user))
        if not user:
            raise TokenError('token error')
        useraddress_list = self.get_useraddress_by_usid(user.USid)
        for useraddress in useraddress_list:
            useraddress.fields = ['UAid', 'UAname', 'UAphone', 'UAtext', 'UApostalcode', 'AAid']
            uadefault = 1 if useraddress.UAdefault is True else 0
            addressinfo = self._get_addressinfo_by_areaid(useraddress.AAid)
            useraddress.fill('addressinfo', addressinfo + getattr(useraddress, 'UAtext', ''))
            useraddress.fill('uadefault', uadefault)
        return Success('获取个人地址成功', data=useraddress_list)

    @get_session
    @token_required
    def add_useraddress(self):
        """添加收货地址"""
        user = self.get_user_by_id(request.user.id)
        gennerc_log('get user is {0}'.format(user))
        if not user:
            raise TokenError('token error')
        data = parameter_required(('uaname', 'uaphone', 'uatext', 'aaid'))
        uaid = str(uuid.uuid1())
        uadefault = data.get('uadefault', 0)
        uaphone = data.get('uaphone')
        uapostalcode = data.get('uapostalcode', '000000')
        if not re.match(r'^[0|1]$', str(uadefault)):
            raise ParamsError('uadefault, 参数异常')
        if not re.match(r'^1[3|4|5|7|8|9][0-9]{9}$', str(uaphone)):
            raise ParamsError('请填写正确的手机号码')
        if not re.match(r'^\d{6}$', str(uapostalcode)):
            raise ParamsError('请输入正确的六位邮编')
        default_address = self.get_useraddress_by_filter({'UAdefault': True, 'isdelete': False})
        if default_address:
            if str(uadefault) == '1':
                updateinfo = self.update_useraddress_by_filter({'UAid': default_address.UAid}, {'UAdefault': False})
                if not updateinfo:
                    raise SystemError('服务器繁忙')
                uadefault = True
            else:
                uadefault = False
        else:
            uadefault = True
        address = UserAddress.create({
            'UAid': uaid,
            'USid': request.user.id,
            'UAname': data.get('uaname'),
            'UAphone': uaphone,
            'UAtext': data.get('uatext'),
            'UApostalcode': uapostalcode,
            'AAid': data.get('aaid'),
            'UAdefault': uadefault
        })
        self.session.add(address)
        return Success('创建地址成功', {'uaid': uaid})

    @get_session
    @token_required
    def update_useraddress(self):
        """修改收货地址"""
        user = self.get_user_by_id(request.user.id)
        gennerc_log('get user is {0}'.format(user))
        if not user:
            raise TokenError('token error')
        data = parameter_required(('uaid',))
        uaid = data.get('uaid')
        uadefault = data.get('uadefault')
        uaphone = data.get('uaphone')
        uapostalcode = data.get('uapostalcode')
        uaisdelete = data.get('uaisdelete', 0)
        if not re.match(r'^[0|1]$', str(uaisdelete)):
            raise ParamsError('uaisdelete, 参数异常')
        usaddress = self.get_useraddress_by_filter({'UAid': uaid})
        if not usaddress:
            raise NotFound('未找到要修改的地址信息')
        if str(uaisdelete) == '1' and usaddress.UAdefault is True:
            anyone = self.get_useraddress_by_filter({'isdelete': False, 'UAdefault': False})
            if anyone:
                self.update_useraddress_by_filter({'UAid': anyone.UAid}, {'UAdefault': True})
        uaisdelete = True if str(uaisdelete) == '1' else False
        if uadefault:
            if not re.match(r'^[0|1]$', str(uadefault)):
                raise ParamsError('uadefault, 参数异常')
            default_address = self.get_useraddress_by_filter({'UAdefault': True, 'isdelete': False})
            if default_address:
                if str(uadefault) == '1':
                    updateinfo = self.update_useraddress_by_filter({'UAid': default_address.UAid}, {'UAdefault': False})
                    if not updateinfo:
                        raise SystemError('服务器繁忙')
                    uadefault = True
                else:
                    uadefault = False
            else:
                uadefault = True
        if uaphone:
            if not re.match(r'^1[3|4|5|7|8|9][0-9]{9}$', str(uaphone)):
                raise ParamsError('请填写正确的手机号码')
        if uapostalcode:
            if not re.match(r'^\d{6}$', str(uapostalcode)):
                raise ParamsError('请输入正确的六位邮编')
        address_dict = {
            'UAname': data.get('uaname'),
            'UAphone': uaphone,
            'UAtext': data.get('uatext'),
            'UApostalcode': uapostalcode,
            'AAid': data.get('aaid'),
            'UAdefault': uadefault,
            'updatetime': datetime.datetime.now(),
            'isdelete': uaisdelete
        }
        address_dict = {k: v for k, v in address_dict.items() if v is not None}
        update_info = self.update_useraddress_by_filter({'UAid': uaid}, address_dict)
        if not update_info:
            raise SystemError('服务器繁忙')
        return Success('修改地址成功', {'uaid': uaid})

    @get_session
    @token_required
    def get_one_address(self):
        """获取单条地址信息详情"""
        user = self.get_user_by_id(request.user.id)
        gennerc_log('get user is {0}'.format(user))
        if not user:
            raise TokenError('token error')
        args = request.args.to_dict()
        uaid = args.get('uaid')
        if uaid:
            uafilter = {'UAid': uaid, 'isdelete': False}
        else:
            uafilter = {'UAdefault': True, 'isdelete': False}
        get_address = self.get_useraddress_by_filter(uafilter)
        any_address = self.get_useraddress_by_filter({'isdelete': False})
        if not any_address:
            raise NotFound('用户未设置任何地址信息')
        address = get_address or any_address
        addressinfo = self._get_addressinfo_by_areaid(address.AAid)
        address.fill('addressinfo', addressinfo + getattr(address, 'UAtext', ''))
        uadefault = 1 if address.UAdefault is True else 0
        address.fill('uadefault', uadefault)
        address.hide('USid')
        return Success(data=address)

    @get_session
    def get_all_province(self):
        """获取所有省份信息"""
        province_list = self.get_province()
        gennerc_log('This is to get province list')
        if not province_list:
            raise NotFound('未找到省份信息')
        return Success(data=province_list)

    @get_session
    def get_citys_by_provinceid(self):
        """获取省份下的城市"""
        args = parameter_required(('apid',))
        gennerc_log('This to get city, provibceid is {0}'.format(args))
        provinceid = args.get('apid')
        city_list = self.get_citylist_by_provinceid(provinceid)
        if not city_list:
            raise NotFound('未找到该省下的城市信息')
        return Success(data=city_list)

    @get_session
    def get_areas_by_cityid(self):
        """获取城市下的区县"""
        args = parameter_required(('acid',))
        gennerc_log('This to get area info, cityid is {0}'.format(args))
        cityid = args.get('acid')
        area_list = self.get_arealist_by_cityid(cityid)
        if not area_list:
            raise NotFound('未找到该城市下的区县信息')
        return Success(data=area_list)

    def _get_addressinfo_by_areaid(self, areaid):
        """通过areaid获取地址具体信息, 返回xx省xx市xx区字符串"""
        area_info = self.get_addressinfo_by_areaid(areaid)
        for area, city, province in area_info:
            address = getattr(province, "APname", '') + ' ' + getattr(city, "ACname", '') + ' ' + getattr(
                area, "AAname", '') + ' '
        return address
