import json
import random
import re

import datetime
import uuid
from decimal import Decimal

from flask import request
from sqlalchemy import extract, or_
from werkzeug.security import generate_password_hash

from planet.config.cfgsetting import ConfigSettings
from planet.config.enums import UserIntegralType, AdminLevel, AdminStatus
from planet.common.params_validates import parameter_required
from planet.common.error_response import ParamsError, SystemError, TokenError, TimeError, NotFound, AuthorityError
from planet.common.success_response import Success
from planet.common.base_service import get_session
from planet.common.token_handler import token_required, usid_to_token, is_shop_keeper, is_hign_level_admin, is_admin
from planet.common.default_head import GithubAvatarGenerator
from planet.common.Inforsend import SendSMS
from planet.common.request_handler import gennerc_log
from planet.common.id_check import DOIDCheck

from planet.models.user import User, UserLoginTime, UserCommission, \
    UserAddress, IDCheck, IdentifyingCode, UserMedia, UserIntegral, Admin, AdminNotes
from .BaseControl import BASEAPPROVAL
from planet.service.SUser import SUser
from planet.models.product import Products, Items, ProductItems
from planet.models.trade import OrderPart


class CUser(SUser, BASEAPPROVAL):
    APPROVAL_TYPE = 1
    AGENT_TYPE = 2
    POPULAR_NAME = '爆款'
    USER_FIELDS = ['USname', 'USheader', 'USintegral', 'USidentification', 'USlevel', 'USgender',
            'UStelphone', 'USqrcode', 'USrealname', 'USbirthday', "USpaycode"]


    @staticmethod
    def __conver_idcode(idcode):
        """掩盖部分身份证号码"""
        if not idcode:
            return ''
        return idcode[:6] + "*" * 12

    def __update_birthday_str(self, birthday_date):
        """变更用户生日展示"""
        if not isinstance(birthday_date, datetime.datetime):
            return ""

        return birthday_date.strftime('%Y-%m-%d')

    def __check_qualifications(self, user):
        """申请代理商资质验证"""
        check_result = True
        check_reason = []
        if not user.UStelphone:
            check_result = False
            check_reason.append("手机号未绑定")
        if not (user.USrealname and user.USidentification):
            check_result = False
            check_reason.append("实名认证未通过")
        # todo 创建押金订单
        return check_result, check_reason[:]

    def __check_password(self, password):
        if not password or len(password) < 4:
            raise ParamsError('密码长度低于4位')
        zh_pattern = re.compile(r'[\u4e00-\u9fa5]+')
        match = zh_pattern.search(password)
        if match:
            raise ParamsError(u'密码包含中文字符')
        return True

    def __check_adname(self, adname, adid):
        """账户名校验"""
        if not adname or adid:
            return True
        suexist = self.session.query(Admin).filter(Admin.ADname == adname).first()
        if suexist and suexist.ADid != adid:
            raise ParamsError('用户名已存在')
        return True

    def __check_identifyingcode(self, ustelphone, identifyingcode):
        """验证码校验"""
        # identifyingcode = str(data.get('identifyingcode'))
        if not ustelphone or not identifyingcode:
            raise ParamsError("验证码/手机号缺失")
        idcode = self.get_identifyingcode_by_ustelphone(ustelphone)

        if not idcode or str(idcode.ICcode) != identifyingcode:
            gennerc_log('get identifyingcode ={0} get idcode = {1}'.format(identifyingcode, idcode.ICcode))
            raise ParamsError('验证码有误')

        timenow = datetime.datetime.now()
        if (timenow - idcode.createtime).seconds > 600:
            gennerc_log('get timenow ={0}, sendtime = {1}'.format(timenow, idcode.createtime))
            raise ParamsError('验证码已经过期')
        return True

    @get_session
    def login(self):
        """手机验证码登录"""
        data = parameter_required(('ustelphone', 'identifyingcode'))
        ustelphone = data.get('ustelphone')
        self.__check_identifyingcode(ustelphone, data.get("identifyingcode"))
        user = self.get_user_by_ustelphone(ustelphone)
        if not user:
            usid = str(uuid.uuid1())
            uslevel = 1
            default_head_path = GithubAvatarGenerator().save_avatar(usid)
            user = User.create({
                "USid": usid,
                "USname": '客官'+str(ustelphone)[-4:],
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
        user.fields = self.USER_FIELDS
        user.fill('usidentification', self.__conver_idcode(user.USidentification))
        user.fill('usbirthday', self.__update_birthday_str(user.USbirthday))
        user.fill('usidname', '行装会员' if uslevel != self.AGENT_TYPE else "合作伙伴")
        token = usid_to_token(usid, model='User', level=uslevel)
        return Success('登录成功', data={'token': token, 'user': user})

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
                "USname": '客官' + str(ustelphone)[-4:],
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
        user.fields = self.USER_FIELDS
        user.fill('usidentification', self.__conver_idcode(user.USidentification))
        user.fill('usbirthday', self.__update_birthday_str(user.USbirthday))
        user.fill('usidname', '行装会员' if uslevel != self.AGENT_TYPE else "合作伙伴")
        self.session.add(userloggintime)
        token = usid_to_token(usid, model='User', level=uslevel)
        print(token, type(token))
        return Success('登录成功', data={'token': token, 'user': user})

    @get_session
    def get_inforcode(self):
        """发送/校验验证码"""
        args = request.args.to_dict()
        print('get inforcode args: {0}'.format(args))
        Utel = args.get('ustelphone')
        if not Utel:
            raise ParamsError('手机号不能为空')
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
        # user.fields = ['USname', 'USintegral','USheader', 'USlevel', 'USqrcode', 'USgender']
        user.fields = self.USER_FIELDS
        user.fill('usidentification', self.__conver_idcode(user.USidentification))
        user.fill('usbirthday', self.__update_birthday_str(user.USbirthday))
        user.fill('usidname', '行装会员' if user.USlevel != self.AGENT_TYPE else "合作伙伴")
        return Success('获取首页用户信息成功', data=user)

    @get_session
    @token_required
    def get_identifyinginfo(self):
        """获取个人身份证详情"""
        user = self.get_user_by_id(request.user.id)
        gennerc_log('get user is {0}'.format(user))
        if not user:
            raise ParamsError('token error')
        user.fields = ['USname', 'USrealname', 'USheader', 'USlevel', 'USgender']
        umfront = self.get_usermedia(user.USid, 1)
        if umfront:
            user.fill('umfront', umfront.UMurl)
        else:
            user.fill('umfront',None)
        umback = self.get_usermedia(user.USid, 2)
        if umback:
            user.fill('umback', umback.UMurl)
        else:
            user.fill('umback', None)
        user.fill('usidentification', self.__conver_idcode(user.USidentification))
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
            uafilter = {'USid': user.USid, 'UAdefault': True, 'isdelete': False}
        get_address = self.get_useraddress_by_filter(uafilter)
        any_address = self.get_useraddress_by_filter({'USid': user.USid, 'isdelete': False})
        if not any_address:
            raise NotFound('用户未设置任何地址信息')
        address = get_address or any_address
        addressinfo = self._get_addressinfo_by_areaid(address.AAid)
        address.fill('areainfo', addressinfo)
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
        area, city, province = self.get_addressinfo_by_areaid(areaid)
        address = getattr(province, "APname", '') + ' ' + getattr(city, "ACname", '') + ' ' + getattr(
            area, "AAname", '') + ' '
        return address

    @get_session
    @token_required
    def check_idcode(self):
        """验证用户身份姓名是否正确"""
        data = parameter_required(('usrealname', 'usidentification', 'umfront', 'umback'))
        name = data.get("usrealname")
        idcode = data.get("usidentification")
        if not (name and idcode):
            raise ParamsError('姓名和身份证号码不能为空')
        idcheck = self.get_idcheck_by_name_code(name, idcode)
        if not idcheck:
            idcheck = DOIDCheck(name, idcode)
            newidcheck_dict = {
                "IDCid": str(uuid.uuid1()),
                "IDCcode": idcheck.idcode,
                "IDCname": idcheck.name,
                "IDCresult": idcheck.result
            }
            if idcheck.result:
                newidcheck_dict['IDCrealName'] = idcheck.check_response.get('result').get('realName')
                newidcheck_dict['IDCcardNo'] = idcheck.check_response.get('result').get('cardNo')
                newidcheck_dict['IDCaddrCode'] = idcheck.check_response.get('result').get('details').get('addrCode')
                newidcheck_dict['IDCbirth'] = idcheck.check_response.get('result').get('details').get('birth')
                newidcheck_dict['IDCsex'] = idcheck.check_response.get('result').get('details').get('sex')
                newidcheck_dict['IDCcheckBit'] = idcheck.check_response.get('result').get('details').get('checkBit')
                newidcheck_dict['IDCaddr'] = idcheck.check_response.get('result').get('details').get('addr')
                newidcheck_dict['IDCerrorCode'] = idcheck.check_response.get('error_code')
                newidcheck_dict['IDCreason'] = idcheck.check_response.get('reason')
            else:
                newidcheck_dict['IDCerrorCode'] = idcheck.check_response.get('error_code')
                newidcheck_dict['IDCreason'] = idcheck.check_response.get('reason')
            newidcheck = IDCheck.create(newidcheck_dict)
            check_result = idcheck.result
            check_message = idcheck.check_response.get('reason')
            self.session.add(newidcheck)
        else:
            check_message = idcheck.IDCreason
            check_result = idcheck.IDCresult

        if check_result:
            # 如果验证成功，更新用户信息
            update_result = self.update_user_by_filter(us_and_filter=[User.USid == request.user.id], us_or_filter=[],
                                       usinfo={"USrealname": name, "USidentification": idcode})
            if not update_result:
                gennerc_log('update user error usid = {0}, name = {1}, identification = {2}'.format(
                    request.user.id, name, idcode), info='error')
                raise SystemError('服务器异常')
            self.delete_usemedia_by_usid(request.user.id)
            um_front = UserMedia.create({
                "UMid": str(uuid.uuid1()),
                "USid": request.user.id,
                "UMurl": data.get("umfront"),
                "UMtype": 1
            })
            um_back = UserMedia.create({
                "UMid": str(uuid.uuid1()),
                "USid": request.user.id,
                "UMurl": data.get("umback"),
                "UMtype": 2
            })
            self.session.add(um_front)
            self.session.add(um_back)
        return Success('获取验证信息成功', data={'result': check_result, 'reason': check_message})

    @get_session
    @token_required
    def upgrade_agent(self):
        """申请成为店主"""
        data = request.json or {}
        user = self.get_user_by_id(request.user.id)
        if user.USlevel == self.AGENT_TYPE:
            raise AuthorityError('已经是店主了！！！')
        if user.USlevel == 3:
            raise AuthorityError("已经提交了审批！！！")
        # 如果需要可以在此更新自己联系方式以及性别。
        if data.get('ustelphone'):
            user.UStelphone = data.get("ustelphone")
        if data.get('usrealname') and user.USrealname != data.get("usrealname"):
            raise ParamsError("当前姓名与验证姓名不符")
        if data.get("usgender"):
            user.USgender = data.get("usgender")
        user.USlevel = 3
        # 资质认证
        check_result, check_reason = self.__check_qualifications(user)
        if check_result:
            # 资质认证ok，创建审批流

            # todo 审批流创建
            self.create_approval(self.APPROVAL_TYPE, request.user.id, request.user.id)

            return Success('申请成功')
        else:
            raise ParamsError(','.join(check_reason))

    @get_session
    @token_required
    def get_upgrade(self):
        """获取店主申请"""
        user = self.get_user_by_id(request.user.id)
        gennerc_log('get user is {0}'.format(user))
        if not user:
            raise ParamsError('token error')
        user.fields = ['USname', 'USrealname', 'USheader', 'USlevel', 'USgender', "UStelphone"]
        user.fill('usidname', '行装会员' if user.USlevel != self.AGENT_TYPE else "合作伙伴")
        return Success('获取店主申请页成功', data=user)

    @get_session
    @token_required
    def update_user(self):
        """更新用户 昵称/性别/绑定电话/头像/出生日期/支付密码"""
        data = request.json
        user = self.get_user_by_id(request.user.id)
        update_params = ['USname', 'UStelphone', 'USgender', 'USheader', 'USpaycode']

        for k in update_params:
            if k == 'UStelphone':
                user_check = self.get_user_by_tel(data.get(k.lower()))
                if user_check and user_check.USid != user.USid:
                    gennerc_log('绑定已绑定手机 tel = {0}, usid = {1}'.format(data.get(k.lower()), user.USid))
                    raise ParamsError("该手机号已经被绑定")
                self.__check_identifyingcode(data.get("ustelphone"), data.get("identifyingcode"))

            if k == 'USpaycode':
                self.__check_identifyingcode(data.get("ustelphone"), data.get("identifyingcode"))

            if data.get(k.lower()):
                setattr(user, k, data.get(k.lower()))
        if data.get('usbirthday'):
            gennerc_log('get usbirthday = {0}'.format(data.get("usbirthday")))
            user.USbirthday = datetime.datetime.strptime(data.get("usbirthday"), '%Y-%m-%d')
        return Success("更新成功")

    @get_session
    @token_required
    def get_agent_center(self):
        """获取店主中心"""
        if not is_shop_keeper():
            gennerc_log('权限不足 id={0} level={1} '.format(request.user.id, request.user.level))
            raise AuthorityError

        agent = self.get_user_by_id(request.user.id)
        gennerc_log('get user is {0}'.format(agent))
        if not agent:
            raise ParamsError('token error')

        today = datetime.datetime.now()
        usercommission_model_month_list = self.session.query(UserCommission).filter(
            UserCommission.USid == request.user.id, UserCommission.UCstatus == 1,
            extract('month', UserCommission.createtime) == today.month,
            extract('year', UserCommission.createtime) == today.year,
        ).all()
        mounth_count = sum(usercommission_model_month.UCcommission for usercommission_model_month in usercommission_model_month_list)
        # for usercommission_model_month in usercommission_model_month_list:
        #     mounth_count += float(usercommission_model_month.UCcommission)
        usercommission_model_list = self.session.query(UserCommission).filter(
            UserCommission.USid == request.user.id, UserCommission.UCstatus == 1
        ).all()
        uc_count = sum(usercommission_model.UCcommission for usercommission_model in usercommission_model_list)
        fens_sql = self.session.query(User).filter(
            or_(User.USsupper1 == request.user.id, User.USsupper2 ==request.user.id))
        fens_count = fens_sql.count()
        fens_mouth_count = fens_sql.filter(
            extract('month', User.createtime) == today.month,
            extract('year', User.createtime) == today.year,
        ).count()
        # todo 活动记录
        activity_count = 2
        # 佣金比例
        # commisision_profit = agent.USCommission or ConfigSettings().get_item('commission', "planetcommision")
        product_sql = self.session.query(Products).filter_by_(CreaterId=request.user.id, PRstatus=0)
        # 最新
        newest_product = product_sql.order_by(Products.createtime.desc()).first()
        if newest_product:
            newest_product.fields = ['PRid', 'PRtitle', 'PRprice', 'PRdescription', 'PRmainpic']

        # 最热
        hottest_product = product_sql.order_by(Products.PRsalesValue.desc()).first()
        if hottest_product:
            hottest_product.fields = ['PRid', 'PRtitle', 'PRprice', 'PRdescription', 'PRmainpic']

        data = {
            'mounth_count': float(mounth_count),
            'uc_count': float(uc_count),
            'fens_count': fens_count,
            'activity_count': activity_count,
            'fens_mouth_count': fens_mouth_count,
            'hottest_product': hottest_product,
            'newest_product': newest_product,
        }
        return Success('获取店主中心数据成功', data=data)

    @get_session
    @token_required
    def get_agent_commission_list(self):
        """获取收益列表"""
        data = request.args.to_dict()
        if data.get('date'):
            if re.match(r'^[1-9]\d{3}-(0[1-9]|1[0-2])$', data.get("date")):
                date_filter = datetime.datetime.strptime(data.get("date"), "%Y-%m")
            elif re.match(r'^[1-9]\d{3}-(0[1-9]|1[0-2])-(0[1-9]|[1-2][0-9]|3[0-1])$', data.get("date")):
                date_filter = datetime.datetime.strptime(data.get("date"), "%Y-%m-%d")
            else:
                raise ParamsError("时间格式不对")
        else:
            date_filter = datetime.datetime.now()
        uc_model_list = self.session.query(UserCommission).filter(
            UserCommission.USid == request.user.id, UserCommission.UCstatus == 1,
            extract('month', UserCommission.createtime) == date_filter.month,
            extract('year', UserCommission.createtime) == date_filter.year,
        ).all()
        uc_mount = 0
        common_list = []
        popular_list = []
        for uc_model in uc_model_list:
            uc_model.fields = ['OMid', 'createtime']
            uc_model.fill('uccommission', float(uc_model.UCcommission))
            uc_mount += float(uc_model.UCcommission)
            op_list = self.session.query(OrderPart).filter(OrderPart.OMid == uc_model.OMid).all()

            if not op_list:
                gennerc_log('已完成订单找不到分单 订单id = {0}'.format(uc_model.OMid))
                raise SystemError('服务器异常')
            is_popular = False
            om_name = []
            for op in op_list:
                om_name.append(str(op.PRtitle))
                itemes = self.session.query(Items).filter(
                    Items.ITid == ProductItems.ITid, ProductItems.PRid == op.PRid).first()
                if itemes and itemes.ITname == self.POPULAR_NAME:
                    is_popular = True
            om_name = "+".join(om_name)
            if is_popular:
                popular_list.append(uc_model)
            else:
                common_list.append(uc_model)
            uc_model.fill('UCname', om_name)
        return Success('获取收益详情', data={
            'usercommission_mount': uc_mount,
            'usercommission_common_list': common_list,
            "usercommission_popular_list": popular_list})

    @get_session
    @token_required
    def user_sign_in(self):
        """用户签到"""
        user = self.get_user_by_id(request.user.id)
        gennerc_log('get user is {0}'.format(user))
        if not user:
            raise ParamsError('token error')

        ui_model = self.session.query(UserIntegral).filter(UserIntegral.USid).order_by(UserIntegral.createtime).first()
        today = datetime.datetime.now()
        if ui_model and ui_model.createtime.date() == today.date():
            raise TimeError('今天已经签到')
        ui = UserIntegral.create({
            'UIid': str(uuid.uuid1()),
            'USid': request.user.id,
            'UIintegral': ConfigSettings().get_item('integralbase', 'integral'),
            'UIaction': 1,
            'UItype': 1
        })
        self.session.add(ui)
        user.USintegral += int(ui.UIintegral)
        return Success('签到成功')

    @get_session
    @token_required
    def get_user_integral(self):
        """获取积分列表"""
        user = self.get_user_by_id(request.user.id)
        uifilter = request.args.to_dict().get("uifilter", "all")
        gennerc_log('get uifilter ={0}'.format(uifilter))
        uifilter = getattr(UserIntegralType, uifilter, None).value
        gennerc_log('get user is {0}'.format(user))
        if not user:
            raise ParamsError('token error')

        ui_list = self.session.query(UserIntegral).filter_(UserIntegral.UItype == uifilter).all_with_page()
        for ui in ui_list:
            ui.fields = ['UIintegral', 'UIaction', 'createtime']

        return Success('获取积分列表完成', data={'usintegral': user.USintegral, 'uilist': ui_list})

    @get_session
    def admin_login(self):
        """管理员登录"""
        data = parameter_required(('adname', 'adpassword'))
        admin = self.get_admin_by_name(data.get('adname'))
        from werkzeug.security import check_password_hash
        # 密码验证
        if admin and check_password_hash(admin.ADpassword, data.get("adpassword")):
            gennerc_log('管理员登录成功 %s' % admin.ADname)
            # 创建管理员登录记录
            ul_instance = UserLoginTime.create({
                "ULTid": str(uuid.uuid1()),
                "USid": admin.ADid,
                "USTip": request.remote_addr,
                "ULtype": 2
            })
            self.session.add(ul_instance)
            token = usid_to_token(admin.ADid, 'Admin', admin.ADlevel)
            admin.fields = ['ADname', 'ADheader', 'ADlevel']

            admin.fill('adlevel', AdminLevel(admin.ADlevel).name)
            admin.fill('adstatus', AdminStatus(admin.ADstatus).name)

            return Success('登录成功', data={'token': token, "admin": admin})
        return ParamsError("用户名或密码错误")

    @get_session
    @token_required
    def add_admin_by_superadmin(self):
        """超级管理员添加普通管理"""
        # todo 待测试

        superadmin = self.get_admin_by_id(request.user.id)
        if not is_hign_level_admin() or superadmin.ADlevel != 1:
            raise AuthorityError('当前非超管权限')

        data = request.json
        gennerc_log("add admin data is %s" % data)
        parameter_required(('adname', 'adpassword'))
        adid = str(uuid.uuid1())
        password = data.get('adpassword')
        # 密码校验
        self.__check_password(password)

        adname = data.get('adname')
        adlevel = getattr(AdminLevel, data.get('adlevel', '普通管理员'), 2).value
        adlevel = 2 if not adlevel else int(adlevel)
        header = data.get('adheader') or GithubAvatarGenerator().save_avatar(adid)
        # 等级校验
        if adlevel not in [1, 2, 3]:
            raise ParamsError('adlevel参数错误')

        # 账户名校验
        self.__check_adname(adname, adid)

        # 创建管理员
        adinstance = Admin.create({
            'ADid': adid,
            'ADname': adname,
            'ADpassword': generate_password_hash(password),
            'ADheader': header,
            'ADlevel': adlevel,
            'ADstatus': 0,
        })
        self.session.add(adinstance)

        # 创建管理员变更记录
        an_instance = AdminNotes.create({
            'ANid': str(uuid.uuid1()),
            'ADid': adid,
            'ANaction': '{0} 创建管理员{1} 等级{2}'.format(superadmin.ADname, adname, adlevel),
            "ANdoneid": request.user.id
        })

        self.session.add(an_instance)
        return Success('创建管理员成功')

    @get_session
    @token_required
    def update_admin(self):
        if not is_admin():
            raise AuthorityError('权限不足')
        data = request.json or {}
        admin = self.get_admin_by_id(request.user.id)
        update_admin = {
            'ADname': data.get("adname"),
            'ADheader': data.get('adheader'),

        }
        password = data.get('adpassword')
        if password:
            self.__check_password(password)
            password = generate_password_hash(password)
            update_admin['ADpassword'] = password

        if admin.ADlevel == AdminLevel.超级管理员.value:
            filter_adid = data.get('adid') or admin.ADid
            if getattr(AdminLevel, data.get('adlevel', ""), ""):
                update_admin['ADlevel'] = getattr(AdminLevel, data.get('adlevel')).value
            if getattr(AdminStatus, data.get('adstatus', ""), ""):
                update_admin['ADstatus'] = getattr(AdminStatus, data.get('adstatus')).value
        else:
            filter_adid = admin.ADid
        self.__check_adname(data.get("adname"), filter_adid)

        update_admin = {k: v for k, v in update_admin.items() if v or v == 0}
        update_result = self.update_admin_by_filter(ad_and_filter=[Admin.ADid == filter_adid], ad_or_filter=[], adinfo=update_admin)
        if not update_result:
            raise ParamsError('管理员不存在')

        return Success("操作成功")
