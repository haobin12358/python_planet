import base64
import json
import os
import random
import re
import datetime
import uuid
from decimal import Decimal

import requests
from flask import request

from flask import current_app
from sqlalchemy import extract, or_, func
from werkzeug.security import generate_password_hash, check_password_hash

from planet.config.cfgsetting import ConfigSettings
from planet.config.enums import UserIntegralType, AdminLevel, AdminStatus, UserIntegralAction, AdminAction, \
    UserLoginTimetype, UserStatus, WXLoginFrom, OrderMainStatus, BankName, ApprovalType, UserCommissionStatus, \
    ApplyStatus, ApplyFrom, ApprovalAction, SupplizerSettementStatus, UserAddressFrom


from planet.config.secret import SERVICE_APPID, SERVICE_APPSECRET, \
    SUBSCRIBE_APPID, SUBSCRIBE_APPSECRET, appid, appsecret
from planet.config.http_config import PLANET_SERVICE, PLANET_SUBSCRIBE, PLANET
from planet.common.params_validates import parameter_required
from planet.common.error_response import ParamsError, SystemError, TokenError, TimeError, NotFound, AuthorityError, \
    WXLoginError, StatusError, InsufficientConditionsError
from planet.common.success_response import Success
from planet.common.base_service import get_session
from planet.common.token_handler import token_required, usid_to_token, is_shop_keeper, is_hign_level_admin, is_admin, \
    admin_required, is_supplizer, common_user
from planet.common.default_head import GithubAvatarGenerator
from planet.common.Inforsend import SendSMS
from planet.common.request_handler import gennerc_log
from planet.common.id_check import DOIDCheck
from planet.common.make_qrcode import qrcodeWithlogo
from planet.extensions.tasks import auto_agree_task
from planet.extensions.weixin.login import WeixinLogin, WeixinLoginError
from planet.extensions.register_ext import mp_server, mp_subscribe, db
from planet.extensions.validates.user import SupplizerLoginForm, UpdateUserCommisionForm

from planet.models import User, UserLoginTime, UserCommission, UserInvitation, \
    UserAddress, IDCheck, IdentifyingCode, UserMedia, UserIntegral, Admin, AdminNotes, CouponUser, UserWallet, \
    CashNotes, UserSalesVolume, Coupon, SignInAward, SupplizerAccount, SupplizerSettlement, SettlenmentApply
from .BaseControl import BASEAPPROVAL
from planet.service.SUser import SUser
from planet.models.product import Products, Items, ProductItems, Supplizer
from planet.models.trade import OrderPart, OrderMain


class CUser(SUser, BASEAPPROVAL):
    APPROVAL_TYPE = 'toagent'

    AGENT_TYPE = 2
    POPULAR_NAME = '爆款'
    USER_FIELDS = ['USname', 'USheader', 'USintegral', 'USidentification', 'USlevel', 'USgender',
            'UStelphone', 'USqrcode', 'USrealname', 'USbirthday', 'USpaycode']

    @staticmethod
    def __conver_idcode(idcode):
        """掩盖部分身份证号码"""
        if not idcode:
            return ''
        return idcode[:6] + "*" * 12
    #
    # @staticmethod
    # def __cover_telephone(tel):
    #     """隐藏部分手机号"""
    #     if not tel:
    #         return ""
    #     return

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

        if not self._check_gift_order():
            check_result = False
            check_reason.append('没有购买开店大礼包')
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
        suexist = self.get_admin_by_name(adname)
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

    def __decode_token(self, model_str):
        """解析token 的 string 为 dict"""
        # if not isinstance(model_str, str):
        #     raise TypeError('参数异常')
        # model_str = s.split('.')[1]
        # model_str = model_str.encode()
        try:
            model_byte = base64.urlsafe_b64decode(model_str + b'=' * (-len(model_str) % 4))
        except:
            raise ParamsError('邀请人参数异常')
        return json.loads(model_byte.decode('utf-8'))

    def _check_gift_order(self, e=None):
        """检查是否购买大礼包"""
        start = datetime.datetime.now().timestamp()
        op_list = OrderPart.query.filter(
            OrderMain.isdelete == False, OrderPart.isdelete == False,
            ProductItems.isdelete == False, Items.isdelete == False,
            OrderMain.USid == request.user.id,
            OrderMain.OMstatus == OrderMainStatus.ready.value,
            OrderPart.PRid == ProductItems.PRid,
            ProductItems.ITid == Items.ITid,
            Items.ITname == '开店大礼包',
            OrderPart.OMid == OrderMain.OMid).all()

        end = datetime.datetime.now().timestamp()
        gennerc_log('连表查询开店大礼包的查询时间为 {0}'.format(float('%.2f' %(end - start))))
        if op_list and e:
            raise StatusError(e)
        return bool(op_list)

    def __user_fill_uw_total(self, user):
        """用户增加用户余额和用户总收益"""
        # 增加待结算佣金
        uw = UserWallet.query.filter_by_(USid=user.USid).first()
        if not uw:
            user.fill('usbalance', 0)
            user.fill('ustotal', 0)
            user.fill('uscash', 0)
        else:
            user.fill('usbalance', uw.UWbalance or 0)
            user.fill('ustotal', uw.UWtotal or 0)
            user.fill('uscash', uw.UWcash or 0)
        ucs = UserCommission.query.filter(
            UserCommission.USid == user.USid,
            UserCommission.UCstatus == UserCommissionStatus.preview.value,
            UserCommission.isdelete == False).all()
        uc_total = sum([Decimal(str(uc.UCcommission)) for uc in ucs])

        user.fill('usexpect', '%.2f' %float(uc_total))


    def _base_decode(self, raw):
        import base64
        return base64.b64decode(raw + '=' * (4 - len(raw) % 4)).decode()

    def _base_encode(self, raw):
        import base64
        raw = raw.encode()
        return base64.b64encode(raw).decode()

    def _get_local_head(self, headurl, openid):
        """转置微信头像到服务器，用以后续二维码生成"""
        data = requests.get(headurl)
        filename = openid + '.png'
        filepath, filedbpath = self._get_path('avatar')
        filedbname = os.path.join(filedbpath, filename)
        filename = os.path.join(filepath, filename)
        with open(filename, 'wb') as head:
            head.write(data.content)

        return filedbname

    def _get_path(self, fold):
        """获取服务器上文件路径"""
        time_now = datetime.datetime.now()
        year = str(time_now.year)
        month = str(time_now.month)
        day = str(time_now.day)
        filepath = os.path.join(current_app.config['BASEDIR'], 'img', fold, year, month, day)
        file_db_path = os.path.join('/img', fold, year, month, day)
        if not os.path.isdir(filepath):
            os.makedirs(filepath)
        return filepath, file_db_path

    def _create_qrcode(self, head, usid, url):
        """创建二维码"""
        savepath, savedbpath = self._get_path('qrcode')
        secret_usid = self._base_encode(usid)
        # url = PLANET_SUBSCRIBE if app_from and  in PLANET_SUBSCRIBE else PLANET_SERVICE
        url = url + '/#/selected?secret_usid={0}'.format(secret_usid)
        # filename = "{0}{1}.png".format(secret_usid, )
        filename = os.path.join(savepath, '{0}.png'.format(secret_usid))
        filedbname = os.path.join(savedbpath, '{0}.png'.format(secret_usid))
        gennerc_log('get basedir {0}'.format(current_app.config['BASEDIR']))
        head = current_app.config['BASEDIR'] + head
        gennerc_log('get head {0}'.format(head))
        qrcodeWithlogo(url, head, filename)
        return filedbname

    def _verify_cardnum(self, num):
        """获取所属行"""
        bank_url = 'https://ccdcapi.alipay.com/validateAndCacheCardInfo.json?cardNo={}&cardBinCheck=true'
        url = bank_url.format(num)
        response = requests.get(url).json()
        if response and response.get('validated'):
            validated = response.get('validated')
            bankname = getattr(BankName, response.get('bank'), None)
            if bankname:
                bankname = bankname.zh_value
            else:
                validated = False
                bankname = None
        else:
            bankname = None
            validated = False

        return Success('获取银行信息成功', data={'cnbankname': bankname, 'validated': validated})

    def __check_card_num(self, num):
        """初步校验卡号"""
        if not num:
            raise ParamsError('卡号不能为空')
        num = re.sub(r'\s+', '', str(num))
        if not num:
            raise ParamsError('卡号不能为空')
        if not (16 <= len(num) <= 19) or not self.__check_bit(num):
            raise ParamsError('请输入正确卡号')
        return True

    def __check_bit(self, num):
        """
        *从不含校验位的银行卡卡号采用Luhm校验算法获得校验位
        *该校验的过程：
        *1、从卡号最后一位数字开始，逆向将奇数位(1、3、5 等等)相加。
        *2、从卡号最后一位数字开始，逆向将偶数位数字(0、2、4等等)，先乘以2（如果乘积为两位数，则将其减去9或个位与十位相加的和），再求和。
        *3、将奇数位总和加上偶数位总和，如果可以被整除，末尾是0 ，如果不能被整除，则末尾为10 - 余数
        """
        num_str_list = list(num[:-1])
        num_str_list.reverse()
        if not num_str_list:
            return False

        num_list = []
        for num_item in num_str_list:
            num_list.append(int(num_item))

        sum_odd = sum(num_list[1::2])
        sum_even = sum([n * 2 if n * 2 < 10 else n * 2 - 9 for n in num_list[::2]])
        luhm_sum = sum_odd + sum_even

        if (luhm_sum % 10) == 0:
            check_num = 0
        else:
            check_num = 10 - (luhm_sum % 10)
        return check_num == int(num[-1])

    def analysis_app_from(self, appfrom):
        # todo app 可能存在问题。
        if appfrom in PLANET_SUBSCRIBE:
            return {
                'appid': SUBSCRIBE_APPID,
                'appsecret': SUBSCRIBE_APPSECRET,
                'url': PLANET_SUBSCRIBE,
                'usfilter': 'USopenid2',
                'apptype': WXLoginFrom.subscribe.value
            }
        elif appfrom in PLANET_SERVICE:
            return {
                'appid': SERVICE_APPID,
                'appsecret': SERVICE_APPSECRET,
                'url': PLANET_SERVICE,
                'usfilter': 'USopenid1',
                'apptype': WXLoginFrom.service.value
            }
        else:
            return {
                'appid': appid,
                'appsecret': appsecret,
                'url': PLANET_SERVICE,
                'usfilter': 'USopenid1',
                'apptype': WXLoginFrom.app.value
            }

    def __check_apply_cash(self, commision_for):
        """校验提现资质"""
        if commision_for == ApplyFrom.user.value:
            user = User.query.filter(User.USid == request.user.id, User.isdelete == False).first()
            if not user or not (user.USrealname and user.USidentification):
                raise InsufficientConditionsError('没有实名认证')

        elif commision_for == ApplyFrom.supplizer.value:
            sa = SupplizerAccount.query.filter(
                SupplizerAccount.SUid == request.user.id, SupplizerAccount.isdelete == False).first()
            if not sa or not (sa.SAbankName and sa.SAbankDetail and sa.SAcardNo and sa.SAcardName and sa.SAcardName
                              and sa.SACompanyName and sa.SAICIDcode and sa.SAaddress and sa.SAbankAccount):
                raise InsufficientConditionsError('账户信息和开票不完整，请补全账户信息和开票信息')

    @get_session
    def login(self):
        """手机验证码登录"""
        data = parameter_required(('ustelphone', 'identifyingcode'))
        ustelphone = data.get('ustelphone')

        fromdict = self.analysis_app_from(data.get('app_from', 'app'))
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
                "USqrcode": self._create_qrcode(default_head_path, usid, fromdict.get('url')),
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
        db.session.add(userloggintime)
        user.fields = self.USER_FIELDS[:]
        user.fill('usidentification', self.__conver_idcode(user.USidentification))
        user.fill('usbirthday', self.__update_birthday_str(user.USbirthday))
        user.fill('usidname', '大行星会员' if uslevel != self.AGENT_TYPE else "合作伙伴")
        self.__user_fill_uw_total(user)

        token = usid_to_token(usid, model='User', level=uslevel, username=user.USname)
        return Success('登录成功', data={'token': token, 'user': user})

    @get_session
    def login_test(self):
        """获取token"""
        data = parameter_required(('ustelphone',))
        ustelphone = data.get('ustelphone')
        fromdict = self.analysis_app_from(data.get('app_from', 'app'))

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
                "USqrcode": self._create_qrcode(default_head_path, usid, fromdict.get('url')),
                "USlevel": uslevel
            })
            db.session.add(user)
        else:
            usid = user.USid
            uslevel = user.USlevel

        # 用户登录记录
        userloggintime = UserLoginTime.create({
            "ULTid": str(uuid.uuid1()),
            "USid": usid,
            "USTip": request.remote_addr
        })
        db.session.add(userloggintime)

        user.fields = self.USER_FIELDS[:]
        user.fill('usidentification', self.__conver_idcode(user.USidentification))
        user.fill('usbirthday', self.__update_birthday_str(user.USbirthday))
        user.fill('usidname', '大行星会员' if uslevel != self.AGENT_TYPE else "合作伙伴")
        self.__user_fill_uw_total(user)
        token = usid_to_token(usid, model='User', level=uslevel, username=user.USname)
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
        db.session.add(newidcode)

        params = {"code": code}
        response_send_message = SendSMS(Utel, params)

        if not response_send_message:
            raise SystemError('发送验证码失败')

        response = {
            'ustelphone': Utel
        }
        return Success('获取验证码成功', data=response)

    # def wx_login(self):
    #     pass

    @token_required
    def get_home(self):
        """获取个人主页信息"""
        user = self.get_user_by_id(request.user.id)
        gennerc_log('get user is {0}'.format(user))
        if not user:
            raise ParamsError('token error')
        # uscoupon = CouponUser.query.filter_(CouponUser.USid == request.user.id).count()
        # 过滤下可以使用的数量
        time_now = datetime.datetime.now()
        count = db.session.query(func.count(CouponUser.COid)).join(
            Coupon, CouponUser.COid == Coupon.COid
        ).filter(
            CouponUser.USid == request.user.id,
            CouponUser.isdelete == False,
            or_(Coupon.COvalidEndTime < time_now, Coupon.COvalidEndTime.is_(None)),
            or_(Coupon.COvalidStartTime > time_now, Coupon.COvalidStartTime.is_(None)),
            CouponUser.UCalreadyUse == False,
        ).first()
        # user.fields = ['USname', 'USintegral','USheader', 'USlevel', 'USqrcode', 'USgender']
        user.fields = self.USER_FIELDS[:]
        user.fill('usidentification', self.__conver_idcode(user.USidentification))
        user.fill('usbirthday', self.__update_birthday_str(user.USbirthday))
        user.fill('usidname', '大行星会员' if user.USlevel != self.AGENT_TYPE else "合作伙伴")
        user.fill('uscoupon', count[0] or 0)
        self.__user_fill_uw_total(user)
        return Success('获取首页用户信息成功', data=user)

    @get_session
    @token_required
    def get_identifyinginfo(self):
        """获取个人身份证详情"""
        user = self.get_user_by_id(request.user.id)
        gennerc_log('get user is {0}'.format(user))
        if not user:
            raise ParamsError('token error')
        user.fields = self.USER_FIELDS[:]

        user.fill('usidentification', self.__conver_idcode(user.USidentification))
        user.fill('usbirthday', self.__update_birthday_str(user.USbirthday))
        user.fill('usidname', '大行星会员' if user.USlevel != self.AGENT_TYPE else "合作伙伴")
        self.__user_fill_uw_total(user)
        umfront = self.get_usermedia(user.USid, 1)
        if umfront:
            user.fill('umfront', umfront['UMurl'])
        else:
            user.fill('umfront', None)
        umback = self.get_usermedia(user.USid, 2)
        if umback:
            user.fill('umback', umback['UMurl'])
        else:
            user.fill('umback', None)
        user.fill('usidentification', self.__conver_idcode(user.USidentification))
        try:
            admin_info = self.get_admin_by_id(user.USid)
        except:
            admin_info = None

        if admin_info and user.USlevel == 2:
            user.fill('adlevel', AdminLevel(admin_info.ADlevel).zh_value)
            user.fill('adstatus', AdminStatus(admin_info.ADstatus).zh_value)
            user.fill('adname', admin_info.ADfirstname)
            user.fill('adpassword', str(admin_info.ADfirstpwd))
            user.fill('manager_address', PLANET_SERVICE)

        return Success('获取身份证详情成功', data=user)

    @get_session
    def get_useraddress(self):
        """获取用户地址列表"""
        if common_user():
            usid = request.user.id
            user = self.get_user_by_id(usid)
            current_app.logger.info('User {0} get address list'.format(user.USname))
            uafrom = UserAddressFrom.user.value
        elif is_supplizer():
            usid = request.user.id
            supplizer = self.get_supplizer_by_id(usid)
            current_app.logger.info('Supplizer {0} get address list'.format(supplizer.SUname))
            uafrom = UserAddressFrom.supplizer.value
        else:
            raise TokenError()
        useraddress_list = self.get_useraddress_by_usid(usid, uafrom)
        for useraddress in useraddress_list:
            useraddress.fields = ['UAid', 'UAname', 'UAphone', 'UAtext', 'UApostalcode', 'AAid']
            uadefault = 1 if useraddress.UAdefault is True else 0
            addressinfo = self._get_addressinfo_by_areaid(useraddress.AAid)
            useraddress.fill('addressinfo', addressinfo[0] + getattr(useraddress, 'UAtext', ''))
            useraddress.fill('uadefault', uadefault)
            useraddress.fill('acid', addressinfo[1])
            useraddress.fill('apid', addressinfo[2])
        return Success('获取个人地址成功', data=useraddress_list)

    @get_session
    def add_useraddress(self):
        """添加收货地址"""
        if common_user():
            usid = request.user.id
            user = self.get_user_by_id(usid)
            current_app.logger.info('User {0} add address'.format(user.USname))
            uafrom = UserAddressFrom.user.value
        elif is_supplizer():
            usid = request.user.id
            supplizer = self.get_supplizer_by_id(usid)
            current_app.logger.info('Supplizer {0} add address'.format(supplizer.SUname))
            uafrom = UserAddressFrom.supplizer.value
        else:
            raise TokenError()
        data = parameter_required(('uaname', 'uaphone', 'uatext', 'aaid'))
        uaid = str(uuid.uuid1())
        uadefault = data.get('uadefault', 0)
        uaphone = data.get('uaphone')
        uapostalcode = data.get('uapostalcode', '000000')
        aaid = data.get('aaid')
        if not re.match(r'^[01]$', str(uadefault)):
            raise ParamsError('uadefault, 参数异常')
        if not re.match(r'^1[345789][0-9]{9}$', str(uaphone)):
            raise ParamsError('请填写正确的手机号码')
        if not re.match(r'^\d{6}$', str(uapostalcode)):
            raise ParamsError('请输入正确的六位邮编')
        self.get_addressinfo_by_areaid(aaid)
        default_address = self.get_useraddress_by_filter({'USid': usid, 'UAFrom': uafrom, 'UAdefault': True,
                                                          'isdelete': False})
        if default_address:
            if str(uadefault) == '1':
                updateinfo = self.update_useraddress_by_filter({'UAid': default_address.UAid, 'isdelete': False},
                                                               {'UAdefault': False})
                if not updateinfo:
                    raise SystemError('服务器繁忙')
                uadefault = True
            else:
                uadefault = False
        else:
            uadefault = True
        address = UserAddress.create({
            'UAid': uaid,
            'USid': usid,
            'UAname': data.get('uaname'),
            'UAphone': uaphone,
            'UAtext': data.get('uatext'),
            'UApostalcode': uapostalcode,
            'AAid': aaid,
            'UAdefault': uadefault,
            'UAFrom': uafrom
        })
        db.session.add(address)
        return Success('创建地址成功', {'uaid': uaid})

    @get_session
    def update_useraddress(self):
        """修改收货地址"""
        if common_user():
            usid = request.user.id
            user = self.get_user_by_id(usid)
            current_app.logger.info('User {0} update address'.format(user.USname))
            uafrom = UserAddressFrom.user.value
        elif is_supplizer():
            usid = request.user.id
            supplizer = self.get_supplizer_by_id(usid)
            current_app.logger.info('Supplizer {0} update address'.format(supplizer.SUname))
            uafrom = UserAddressFrom.supplizer.value
        else:
            raise TokenError()
        data = parameter_required(('uaid',))
        uaid = data.get('uaid')
        uadefault = data.get('uadefault')
        uaphone = data.get('uaphone')
        uapostalcode = data.get('uapostalcode')
        uaisdelete = data.get('uaisdelete', 0)
        aaid = data.get('aaid')
        if not re.match(r'^[01]$', str(uaisdelete)):
            raise ParamsError('uaisdelete, 参数异常')
        usaddress = self.get_useraddress_by_filter({'UAid': uaid, 'isdelete': False})
        if not usaddress:
            raise NotFound('未找到要修改的地址信息')
        assert usaddress.USid == usid, '只能修改自己账户下的地址'
        if aaid:
            self.get_addressinfo_by_areaid(aaid)
        if str(uaisdelete) == '1' and usaddress.UAdefault is True:
            anyone = self.get_useraddress_by_filter({'USid': usid, 'UAFrom': uafrom, 'isdelete': False,
                                                     'UAdefault': False})
            if anyone:
                self.update_useraddress_by_filter({'UAid': anyone.UAid, 'isdelete': False}, {'UAdefault': True})
        uaisdelete = True if str(uaisdelete) == '1' else False
        if uadefault:
            if not re.match(r'^[01]$', str(uadefault)):
                raise ParamsError('uadefault, 参数异常')
            default_address = self.get_useraddress_by_filter({'USid': usid, 'UAFrom': uafrom, 'UAdefault': True,
                                                              'isdelete': False})
            if default_address:
                if str(uadefault) == '1':
                    updateinfo = self.update_useraddress_by_filter({'UAid': default_address.UAid, 'isdelete': False},
                                                                   {'UAdefault': False})
                    if not updateinfo:
                        raise SystemError('服务器繁忙')
                    uadefault = True
                else:
                    uadefault = False
            else:
                uadefault = True
        if uaphone:
            if not re.match(r'^1[345789][0-9]{9}$', str(uaphone)):
                raise ParamsError('请填写正确的手机号码')
        if uapostalcode:
            if not re.match(r'^\d{6}$', str(uapostalcode)):
                raise ParamsError('请输入正确的六位邮编')
        address_dict = {
            'UAname': data.get('uaname'),
            'UAphone': uaphone,
            'UAtext': data.get('uatext'),
            'UApostalcode': uapostalcode,
            'AAid': aaid,
            'UAdefault': uadefault,
            'updatetime': datetime.datetime.now(),
            'isdelete': uaisdelete
        }
        address_dict = {k: v for k, v in address_dict.items() if v is not None}
        update_info = self.update_useraddress_by_filter({'UAid': uaid, 'isdelete': False}, address_dict)
        if not update_info:
            raise SystemError('服务器繁忙')
        return Success('修改地址成功', {'uaid': uaid})

    @get_session
    def get_one_address(self):
        """获取单条地址信息详情"""
        if common_user():
            usid = request.user.id
            user = self.get_user_by_id(usid)
            current_app.logger.info('User {0} get address content'.format(user.USname))
            uafrom = UserAddressFrom.user.value
        elif is_supplizer():
            usid = request.user.id
            supplizer = self.get_supplizer_by_id(usid)
            current_app.logger.info('Supplizer {0} get address content'.format(supplizer.SUname))
            uafrom = UserAddressFrom.supplizer.value
        else:
            raise TokenError()
        args = request.args.to_dict()
        uaid = args.get('uaid')
        if uaid:
            uafilter = {'UAid': uaid, 'isdelete': False}
        else:
            uafilter = {'USid': user.USid, 'UAFrom': uafrom, 'UAdefault': True, 'isdelete': False}
        address = self.get_useraddress_by_filter(uafilter) or self.get_useraddress_by_filter({'USid': user.USid,
                                                                                              'isdelete': False})
        if not address:
            raise NotFound('用户未设置任何地址信息')
        addressinfo = self._get_addressinfo_by_areaid(address.AAid)
        address.fill('areainfo', addressinfo[0])
        address.fill('addressinfo', addressinfo[0] + getattr(address, 'UAtext', ''))
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
        try:
            area, city, province = self.get_addressinfo_by_areaid(areaid)
        except Exception as e:
            gennerc_log("NOT FOUND this areaid, ERROR is {}".format(e))
            province = {"APname": '', "APid": ''}
            city = {"ACname": '', "ACid": ''}
            area = {"AAname": ''}
        address = getattr(province, "APname", '') + ' ' + getattr(city, "ACname", '') + ' ' + getattr(
            area, "AAname", '') + ' '
        return address, city['ACid'], province['APid']

    # @get_session
    # @token_required
    def check_idcode(self, data, user):
        """验证用户身份姓名是否正确"""

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
            db.session.add(newidcheck)
        else:
            check_message = idcheck.IDCreason
            check_result = idcheck.IDCresult

        if check_result:
            # 如果验证成功，更新用户信息
            # update_result = self.update_user_by_filter(us_and_filter=[User.USid == request.user.id], us_or_filter=[],
            #                            usinfo={"USrealname": name, "USidentification": idcode})
            # if not update_result:
            #     gennerc_log('update user error usid = {0}, name = {1}, identification = {2}'.format(
            #         request.user.id, name, idcode), info='error')
            #     raise SystemError('服务器异常')
            user.USrealname = name
            user.USidentification = idcode
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
            db.session.add(um_front)
            db.session.add(um_back)
            return Success('实名认证成功', data=check_message)
        raise ParamsError('实名认证失败：{0}'.format(check_message))
        # return Success('获取验证信息成功', data={'result': check_result, 'reason': check_message})

    @get_session
    @token_required
    def upgrade_agent(self):
        """申请成为店主"""
        data = parameter_required(('usrealname', 'usidentification', 'umfront', 'umback'))
        user = self.get_user_by_id(request.user.id)
        if user.USlevel == self.AGENT_TYPE:
            raise AuthorityError('已经是店主了！！！')
        if user.USlevel == 3:
            raise AuthorityError("已经提交了审批！！！")
        # 如果需要可以在此更新自己联系方式以及性别。
        # if data.get('ustelphone'):
        #     user.UStelphone = data.get("ustelphone")

        if data.get("usgender"):
            user.USgender = data.get("usgender")

        user.USlevel = 3
        # 资质认证
        self.check_idcode(data, user)
        check_result, check_reason = self.__check_qualifications(user)
        db.session.flush()
        if check_result:
            # 资质认证ok，创建审批流
            avid = self.create_approval(self.APPROVAL_TYPE, request.user.id, request.user.id)
            auto_agree_task.apply_async(args=[avid], countdown=2 * 7, expires=10 * 60)
            # todo 遍历邀请历史，将未成为店主以及未成为其他店主粉丝的粉丝绑定为自己的粉丝在审批完成之后实现
            # 创建后台账号用其手机号作为账号
            # adid = str(uuid.
            # ())
            # adinstance = Admin.create({
            #     'ADid': user.USid,
            #     'ADname': str(user.UStelphone),
            #     'ADtelphone': str(user.UStelphone),
            #     'ADfirstname': str(user.UStelphone),
            #     'ADpassword': generate_password_hash(str(user.UStelphone[-6:])),
            #     'ADfirstpwd': str(user.UStelphone[-6:]),
            #     'ADheader': user.USheader,
            #     'ADlevel': 3,
            #     'ADstatus': 0,
            # })
            # an_instance = AdminNotes.create({
            #     'ANid': str(uuid.uuid1()),
            #     'ADid': user.USid,
            #     'ANaction': '{0}申请代理商创建管理员{1} 等级{2}'.format(user.USname, adinstance.ADname, adinstance.ADlevel),
            #     "ANdoneid": request.user.id
            # })
            # db.session.add(adinstance)
            # db.session.add(an_instance)
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
        user.fill('usidname', '大行星会员' if user.USlevel != self.AGENT_TYPE else "合作伙伴")
        return Success('获取店主申请页成功', data=user)

    @get_session
    @token_required
    def update_user(self):
        """更新用户 昵称/性别/绑定电话/头像/出生日期/支付密码"""
        data = request.json
        user = self.get_user_by_id(request.user.id)
        update_params = ['USname', 'UStelphone', 'USgender', 'USheader', 'USpaycode']

        for k in update_params:
            if data.get(k.lower()) or data.get(k.lower()) == 0:
                if k == 'UStelphone':
                    user_check = self.get_user_by_tel(data.get(k.lower()))
                    if user_check and user_check.USid != user.USid:
                        gennerc_log('绑定已绑定手机 tel = {0}, usid = {1}'.format(data.get(k.lower()), user.USid))
                        raise ParamsError("该手机号已经被绑定")
                    self.__check_identifyingcode(data.get("ustelphone"), data.get("identifyingcode"))
                if k == 'USpaycode':
                    self.__check_identifyingcode(data.get("ustelphone"), data.get("identifyingcode"))
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
        self.__user_fill_uw_total(agent)
        gennerc_log('get user is {0}'.format(agent))
        if not agent:
            raise ParamsError('token error')

        today = datetime.datetime.now()
        usercommission_model_month_list = self.get_ucmonth_by_usid(request.user.id, today)
        mounth_count = sum(usercommission_model_month.UCcommission for usercommission_model_month in usercommission_model_month_list)
        # for usercommission_model_month in usercommission_model_month_list:
        #     mounth_count += float(usercommission_model_month.UCcommission)
        usercommission_model_list = self.get_ucall_by_usid(request.user.id)
        uc_count = sum(usercommission_model.UCcommission for usercommission_model in usercommission_model_list)
        fens_sql = User.query.filter(User.isdelete == False,
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
        product_sql = Products.query.filter_by_(CreaterId=request.user.id, PRstatus=0)
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
            'usbalance': agent.usbalance
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
        uc_model_list = self.get_ucmonth_by_usid(request.user.id, date_filter)
        uc_mount = 0
        # common_list = []
        # popular_list = []
        for uc_model in uc_model_list:
            uc_model.fields = ['createtime', 'UCcommission', 'PRtitle', 'SKUpic']
            uc_model.fill('uccommission', float(uc_model.UCcommission))
            uc_mount += float(uc_model.UCcommission)
            op_list = OrderPart.query.filter(OrderPart.OMid == uc_model.OMid, OrderPart.isdelete == False).all()

            if not op_list:
                gennerc_log('已完成订单找不到分单 订单id = {0}'.format(uc_model.OMid))
                raise SystemError('服务器异常')
            # is_popular = False
            # om_name = []
            # for op in op_list:
            #     om_name.append(str(op.PRtitle))
            #     itemes = Items.query.filter(
            #         Items.ITid == ProductItems.ITid, ProductItems.PRid == op.PRid).first()
            #     if itemes and itemes.ITname == self.POPULAR_NAME:
            #         is_popular = True
            # om_name = "+".join(om_name)
            # # if is_popular:
            # #     popular_list.append(uc_model)
            # # else:
            # #     common_list.append(uc_model)
            # uc_model.fill('UCname', om_name)
        return Success('获取收益详情', data={
            'usercommission_mount': '%.2f' % uc_mount,
            'usercommission_common_list': uc_model_list,
            # "usercommission_popular_list": popular_list
        })

    @get_session
    @token_required
    def user_sign_in(self):
        """用户签到"""
        user = self.get_user_by_id(request.user.id)

        if not user:
            raise ParamsError('token error')

        ui_model = UserIntegral.query.filter_by_(USid=request.user.id, UIaction=UserIntegralAction.signin.value)\
            .order_by(UserIntegral.createtime.desc()).first()

        today = datetime.datetime.now()

        yesterday = today - datetime.timedelta(days=1)
        if ui_model:
            gennerc_log('ui model time %s , today date %s' % (ui_model.createtime.date(), today.date()))

            if ui_model.createtime.date() == today.date():
                raise TimeError('今天已经签到')
            elif ui_model.createtime.date() == yesterday.date():
                gennerc_log('连续签到增加天数 原来是 %s' % user.UScontinuous)
                user.UScontinuous = (user.UScontinuous or 0) + 1
                gennerc_log('更新后为 uscontinuous %s' %user.UScontinuous)
            else:
                user.UScontinuous = 1
                gennerc_log('今天开始重新签到 uscontinuous %s' % user.UScontinuous)
        else:
            user.UScontinuous = 1
            gennerc_log('今天是第一次签到 uscontinuous %s' % user.UScontinuous)

        integral = SignInAward.query.filter(
            SignInAward.SIAday >= user.UScontinuous, SignInAward.isdelete == False).order_by(SignInAward.SIAday).first()
        if not integral:
            integral = ConfigSettings().get_item('integralbase', 'integral')
        else:
            integral = integral.SIAnum

        ui = UserIntegral.create({
            'UIid': str(uuid.uuid1()),
            'USid': request.user.id,
            'UIintegral': integral,
            'UIaction': UserIntegralAction.signin.value,
            'UItype': UserIntegralType.income.value
        })

        db.session.add(ui)
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

        ui_list = UserIntegral.query.filter_(UserIntegral.USid == request.user.id, UserIntegral.UItype == uifilter).all_with_page()
        for ui in ui_list:
            ui.fields = ['UIintegral', 'createtime']
            ui.fill('uiaction', UserIntegralAction(ui.UIaction).zh_value)

        return Success('获取积分列表完成', data={'usintegral': user.USintegral, 'uilist': ui_list})

    @get_session
    def admin_login(self):
        """管理员登录"""
        data = parameter_required(('adname', 'adpassword'))
        admin = self.get_admin_by_name(data.get('adname'))

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
            db.session.add(ul_instance)
            token = usid_to_token(admin.ADid, 'Admin', admin.ADlevel, username=admin.ADname)
            admin.fields = ['ADname', 'ADheader', 'ADlevel']

            admin.fill('adlevel', AdminLevel(admin.ADlevel).zh_value)
            admin.fill('adstatus', AdminStatus(admin.ADstatus).zh_value)

            return Success('登录成功', data={'token': token, "admin": admin})
        return ParamsError("用户名或密码错误")

    @get_session
    @token_required
    def add_admin_by_superadmin(self):
        """超级管理员添加普通管理"""

        superadmin = self.get_admin_by_id(request.user.id)
        if not is_hign_level_admin() or \
                superadmin.ADlevel != AdminLevel.super_admin.value or\
                superadmin.ADstatus != AdminStatus.normal.value:
            raise AuthorityError('当前非超管权限')

        data = request.json
        gennerc_log("add admin data is %s" % data)
        parameter_required(('adname', 'adpassword', 'adtelphone'))
        adid = str(uuid.uuid1())
        password = data.get('adpassword')
        # 密码校验
        self.__check_password(password)

        adname = data.get('adname')
        adlevel = getattr(AdminLevel, data.get('adlevel', ''))
        adlevel = 2 if not adlevel else int(adlevel.value)
        header = data.get('adheader') or GithubAvatarGenerator().save_avatar(adid)
        # 等级校验
        if adlevel not in [1, 2, 3]:
            raise ParamsError('adlevel参数错误')

        # 账户名校验
        self.__check_adname(adname, adid)
        adnum = self.__get_adnum()
        # 创建管理员
        adinstance = Admin.create({
            'ADid': adid,
            'ADnum': adnum,
            'ADname': adname,
            'ADtelphone': data.get('adtelphone'),
            'ADfirstpwd': password,
            'ADfirstname': adname,
            'ADpassword': generate_password_hash(password),
            'ADheader': header,
            'ADlevel': adlevel,
            'ADstatus': 0,
        })
        db.session.add(adinstance)

        # 创建管理员变更记录
        an_instance = AdminNotes.create({
            'ANid': str(uuid.uuid1()),
            'ADid': adid,
            'ANaction': '{0} 创建管理员{1} 等级{2}'.format(superadmin.ADname, adname, adlevel),
            "ANdoneid": request.user.id
        })

        db.session.add(an_instance)
        return Success('创建管理员成功')

    @get_session
    @token_required
    def update_admin(self):
        """更新管理员信息"""
        if not is_admin():
            raise AuthorityError('权限不足')
        data = request.json or {}
        admin = self.get_admin_by_id(request.user.id)
        if admin.ADstatus != AdminStatus.normal.value:
            raise AuthorityError('权限不足')
        update_admin = {}
        action_list = []
        if data.get("adname"):
            update_admin['ADname'] = data.get("adname")
            action_list.append(str(AdminAction.ADname.value) + '为' + str(data.get("adname")) + '\n')

        if data.get('adheader'):
            update_admin['ADheader'] = data.get("adheader")
            action_list.append(str(AdminAction.ADheader.value) + '\n')
        if data.get('adtelphone'):
            # self.__check_identifyingcode(data.get('adtelphone'), data.get('identifyingcode'))
            update_admin['ADtelphone'] = data.get('adtelphone')
            action_list.append(str(AdminAction.ADtelphone.value) + '为' + str(data.get("adtelphone")) + '\n')
        password = data.get('adpassword')
        if password and password != '*' * 6:
            self.__check_password(password)
            password = generate_password_hash(password)
            update_admin['ADpassword'] = password
            action_list.append(str(AdminAction.ADpassword.value) + '为' + str(password) + '\n')

        if admin.ADlevel == AdminLevel.super_admin.value:
            filter_adid = data.get('adid') or admin.ADid
            if getattr(AdminLevel, data.get('adlevel', ""), ""):
                update_admin['ADlevel'] = getattr(AdminLevel, data.get('adlevel')).value
                action_list.append(
                    str(AdminAction.ADlevel.value) + '为' + getattr(AdminLevel, data.get('adlevel')).zh_value + '\n')
            if getattr(AdminStatus, data.get('adstatus', ""), ""):
                update_admin['ADstatus'] = getattr(AdminStatus, data.get('adstatus')).value
                action_list.append(
                    str(AdminAction.ADstatus.value) + '为' + getattr(AdminStatus, data.get('adstatus')).zh_value + '\n')
        else:
            filter_adid = admin.ADid
        self.__check_adname(data.get("adname"), filter_adid)

        update_admin = {k: v for k, v in update_admin.items() if v or v == 0}
        update_result = self.update_admin_by_filter(ad_and_filter=[Admin.ADid == filter_adid, Admin.isdelete == False], ad_or_filter=[], adinfo=update_admin)
        if not update_result:
            raise ParamsError('管理员不存在')
        filter_admin = self.get_admin_by_id(filter_adid)

        action_str = admin.ADname + '修改' + filter_admin.ADname + ','.join(action_list)

        an_instance = AdminNotes.create({
            'ANid': str(uuid.uuid1()),
            'ADid': filter_adid,
            'ANaction': action_str,
            "ANdoneid": request.user.id
        })
        db.session.add(an_instance)
        return Success("操作成功")

    @get_session
    @token_required
    def get_admin_list(self):
        """获取管理员列表"""
        superadmin = self.get_admin_by_id(request.user.id)
        if not is_hign_level_admin() or \
                superadmin.ADlevel != AdminLevel.super_admin.value or\
                superadmin.ADstatus != AdminStatus.normal.value:
            raise AuthorityError('当前非超管权限')
        args = request.args.to_dict()
        page = args.get('page_num')
        count = args.get('page_size')
        if page and count:
            admins = Admin.query.filter(
                Admin.isdelete == False, Admin.ADlevel == AdminLevel.common_admin.value).order_by(
                Admin.createtime.desc()).all_with_page()
        else:
            admins = Admin.query.filter(
                Admin.isdelete == False, Admin.ADlevel == AdminLevel.common_admin.value).order_by(
                Admin.createtime.desc()).all()
        for admin in admins:
            admin.fields = ['ADid', 'ADname', 'ADheader', 'createtime', 'ADtelphone', 'ADnum']
            admin.fill('adlevel', AdminLevel(admin.ADlevel).zh_value)
            admin.fill('adstatus', AdminStatus(admin.ADstatus).zh_value)
            admin.fill('adpassword', '*' * 6)
            admin_login = UserLoginTime.query.filter_by_(
                USid=admin.ADid, ULtype=UserLoginTimetype.admin.value).order_by(UserLoginTime.createtime.desc()).first()
            logintime = None
            if admin_login:
                logintime = admin_login.createtime
            admin.fill('logintime', logintime)

        return Success('获取管理员列表成功', data=admins)

    @get_session
    def get_wxconfig(self):
        """获取微信参数"""
        url = request.args.get("url", request.url)
        gennerc_log('get url %s' % url)
        app_from = request.args.get('app_from', )
        # todo 根据不同的来源处理不同的mp
        if app_from and app_from in PLANET_SUBSCRIBE:
            data = mp_subscribe.jsapi_sign(url=url)
        else:
            data = mp_server.jsapi_sign(url=url)
        gennerc_log("get wx config %s" % data)
        return Success('获取微信参数成功', data=data)

    @get_session
    def wx_login(self):
        """微信登录"""
        # args = request.args.to_dict()
        args = request.json
        app_from = args.get("app_from")
        # app from : {IOS Android, web1, web2} ps
        code = args.get('code')
        # todo 根据不同的来源处理不同的appid, appsecret

        fromdict = self.analysis_app_from(app_from)
        APP_ID = fromdict.get('appid')
        APP_SECRET_KEY = fromdict.get('appsecret')

        wxlogin = WeixinLogin(APP_ID, APP_SECRET_KEY)

        try:
            data = wxlogin.access_token(args["code"])
        except WeixinLoginError as e:
            gennerc_log(e)
            raise WXLoginError
        openid = data.openid
        access_token = data.access_token
        gennerc_log('get openid = {0} and access_token = {1}'.format(openid, access_token))
        # todo 通过app_from 来通过不同的openid 获取用户
        usfilter = {
            fromdict.get('usfilter'): openid
        }

        user = User.query.filter_by_(usfilter).first()
        if user:
            gennerc_log('wx_login get user by openid : {0}'.format(user.__dict__))
        user_info = wxlogin.userinfo(access_token, openid)
        gennerc_log('wx_login get user info from wx : {0}'.format(user_info))
        head = self._get_local_head(user_info.get("headimgurl"), openid)

        if args.get('secret_usid'):
            try:
                superid = self._base_decode(args.get('secret_usid'))
                upperd = self.get_user_by_id(superid)
                gennerc_log('wx_login get supper user : {0}'.format(upperd.__dict__))
                if user and upperd.USid == user.USid:
                    upperd = None

            except:
                upperd = None
        else:
            upperd = None
        # upperd_id = upperd.USid if upperd else None
        sex = int(user_info.get('sex')) - 1
        if sex < 0:
            sex = 0
        if user:
            # todo 如果用户不想使用自己的微信昵称和微信头像，则不修改 需额外接口。配置额外字段
            usid = user.USid
            user.USheader = head
            user.USname = user_info.get('nickname')
            user.USgender = sex
        else:
            usid = str(uuid.uuid1())
            user_dict = {
                'USid': usid,
                'USname': user_info.get('nickname'),
                'USgender': sex,
                'USheader': head,
                'USintegral': 0,
                'USqrcode': self._create_qrcode(head, usid, fromdict.get('url')),
                'USfrom': fromdict.get('apptype'),
                'USlevel': 1,
            }

            # todo 根据app_from 添加不同的openid, 添加不同的usfrom
            user_dict.setdefault(fromdict.get('usfilter'), openid)
            if upperd:
                # 有邀请者，如果邀请者是店主，则绑定为粉丝，如果不是，则绑定为预备粉丝
                if upperd.USlevel == self.AGENT_TYPE:
                    user_dict.setdefault('USsupper1', upperd.USid)
                    user_dict.setdefault('USsupper2', upperd.USsupper1)
                    user_dict.setdefault('USsupper3', upperd.USsupper2)
                else:
                    uin = UserInvitation.create({
                        'UINid': str(uuid.uuid1()), 'USInviter': upperd.USid, 'USInvited': usid})
                    db.session.add(uin)
            user = User.create(user_dict)
            db.session.add(user)

        userloggintime = UserLoginTime.create({
            "ULTid": str(uuid.uuid1()),
            "USid": usid,
            "USTip": request.remote_addr
        })

        db.session.add(userloggintime)
        user.fields = self.USER_FIELDS[:]
        user.fill('openid', openid)
        user.fill('usidentification', self.__conver_idcode(user.USidentification))
        user.fill('usbirthday', self.__update_birthday_str(user.USbirthday))
        user.fill('usidname', '大行星会员' if user.USlevel != self.AGENT_TYPE else "合作伙伴")
        self.__user_fill_uw_total(user)
        gennerc_log('get user = {0}'.format(user.__dict__))

        token = usid_to_token(user.USid, level=user.USlevel, username=user.USname)
        data = {'token': token, 'user': user, 'is_new': not bool(user.UStelphone)}
        gennerc_log(data)
        return Success('登录成功', data=data)

    @get_session
    @token_required
    def bing_telphone(self):
        """微信绑定后手机号绑定"""
        user_openid = self.get_user_by_id(request.user.id)
        if not user_openid:
            raise ParamsError('token error')
        data = parameter_required(('ustelphone', 'identifyingcode'))
        ustelphone = data.get('ustelphone')
        self.__check_identifyingcode(ustelphone, data.get("identifyingcode"))
        # 检查手机号是否已经注册
        user = self.get_user_by_ustelphone(ustelphone)
        if not user:
            # 如果没有绑定，给当前用户绑定手机号
            usid = user_openid.USid
            uslevel = user_openid.USlevel
            user_openid.UStelphone = data.get('ustelphone')
            return_user = user_openid
        else:
            # 如果已经绑定，删除当前用户，将信息导入到手机绑定账户
            usid = user.USid
            uslevel = user.USlevel
            user_openid.isdelete = True
            user.USname = user_openid.USname
            user.USgender = user_openid.USgender
            user.USheader = user_openid.USheader
            # user.USsupper1 = user_openid.USsupper1
            # user.USsupper2 = user_openid.USsupper2
            user.USopenid1 = user_openid.USopenid1
            # user.USopenid2 = user_openid.USopenid2
            user.USopenid2 = user_openid.USopenid2
            return_user = user

        return_user.fields = self.USER_FIELDS[:]
        return_user.fill('usidentification', self.__conver_idcode(return_user.USidentification))
        return_user.fill('usbirthday', self.__update_birthday_str(return_user.USbirthday))
        return_user.fill('usidname', '大行星会员' if uslevel != self.AGENT_TYPE else "合作伙伴")
        self.__user_fill_uw_total(return_user)
        token = usid_to_token(usid, model='User', level=uslevel, username=return_user.USname)
        return Success('登录成功', data={'token': token, 'user': return_user})


    @get_session
    @token_required
    def get_discount(self):
        """获取优惠中心"""
        user = self.get_user_by_id(request.user.id)
        gennerc_log('get user is {0}'.format(user))
        if not user:
            raise ParamsError('token error')
        today = datetime.datetime.now().date()
        yesterday = today - datetime.timedelta(days=1)
        signintime = UserIntegral.query.filter_by_(USid=request.user.id, UIaction=UserIntegralAction.signin.value). \
            order_by(UserIntegral.createtime.desc()).first()
        if signintime:
            signin_today = bool(today == signintime.createtime.date())
            if yesterday == signintime.createtime.date():
                user.UScontinuous = 0
        else:
            signin_today = False
        cfg = ConfigSettings()
        rule = cfg.get_item('integralrule', 'rule')
        sia_list = SignInAward.query.filter_by(isdelete=False).order_by(SignInAward.SIAday).all()
        dis_dict = {
            'usintegral': user.USintegral,
            'uscontinuous': user.UScontinuous or 0,
            'signin_today': signin_today,
            'integralrule': rule,
            'signrule': sia_list
        }
        return Success('获取优惠中心成功', data=dis_dict)

    @get_session
    @token_required
    def authentication_real_name(self):
        """实名认证"""
        data = parameter_required(('usrealname', 'usidentification', 'umfront', 'umback'))
        user = self.get_user_by_id(request.user.id)

        return self.check_idcode(data, user)

    def supplizer_login(self):
        """供应商登录"""
        # 手机号登录
        form = SupplizerLoginForm().valid_data()
        mobile = form.mobile.data
        password = form.password.data
        supplizer = Supplizer.query.filter_by_({'SUloginPhone': mobile}).first_()
        if not supplizer or not check_password_hash(supplizer.SUpassword, password):
            raise NotFound('手机号或密码错误')
        if supplizer.SUstatus == UserStatus.forbidden.value:
            raise StatusError('账户禁用')
        jwt = usid_to_token(supplizer.SUid, 'Supplizer', username=supplizer.SUname)  # 供应商jwt
        supplizer.fields = ['SUlinkPhone', 'SUheader', 'SUname']
        return Success('登录成功', data={
            'token': jwt,
            'supplizer': supplizer
        })

    @token_required
    def get_secret_usid(self):
        """获取base64编码后的usid"""
        usid = request.user.id

        secret_usid = self._base_encode(usid)
        return Success(data={
            'secret_usid': secret_usid,
        })

    def get_admin_all_type(self):
        """获取后台管理员所有身份"""
        # todo 自动获取可以添加的身份
        # data = [{'value': level.name, 'lable': level.zh_value } for level in AdminLevel]
        data = [{'value': 'common_admin', 'lable': '普通管理员'}]
        # data = {level.name: level.zh_value for level in AdminLevel}
        return Success('获取所有身份成功', data=data)

    def get_admin_all_status(self):
        """获取后台管理员所有状态"""
        # data = {status.name: status.zh_value for status in AdminStatus}
        data = [{'value': status.name, 'lable': status.zh_value} for status in AdminStatus]
        return Success('获取所有状态成功', data=data)

    @get_session
    @token_required
    def update_admin_password(self):
        """更新管理员密码"""
        if not is_admin():
            raise AuthorityError('权限不足')

        data = parameter_required(('password_old', 'password_new', 'password_repeat'))
        admin = self.get_admin_by_id(request.user.id)
        pwd_new = data.get('password_new')
        pwd_old = data.get('password_old')
        pwd_repeat = data.get('password_repeat')
        if pwd_new != pwd_repeat:
            raise ParamsError('两次输入的面膜不同')
        if admin:
            if check_password_hash(admin.ADpassword, pwd_old):
                self.__check_password(pwd_new)
                admin.ADpassword = generate_password_hash(pwd_new)
                return Success('更新密码成功')
            gennerc_log('{0} update pwd failed'.format(admin.ADname))
            raise ParamsError('旧密码有误')

        raise AuthorityError('账号已被回收')

    @get_session
    @token_required
    def apply_cash(self):
        if is_admin():
            commision_for = ApplyFrom.platform.value
        elif is_supplizer():
            commision_for = ApplyFrom.supplizer.value
        else:
            commision_for = ApplyFrom.user.value
        # 提现资质校验
        self.__check_apply_cash(commision_for)
        # data = parameter_required(('cncashnum', 'cncardno', 'cncardname', 'cnbankname', 'cnbankdetail'))
        data = parameter_required(('cncashnum',))
        # if not is_shop_keeper():
        #     raise AuthorityError('权限不足')
        # user = self.get_user_by_id(reqbuest.user.id)
        # if user.USlevel != self.AGENT_TYPE:
        #     raise AuthorityError('代理商权限过期')
        uw = UserWallet.query.filter(
            UserWallet.USid == request.user.id,
            UserWallet.isdelete == False,
            UserWallet.CommisionFor == commision_for
        ).first()
        balance = uw.UWcash if uw else 0
        if float(data.get('cncashnum')) > float(balance):
            gennerc_log('提现金额为 {0}  实际余额为 {1}'.format(data.get('cncashnum'), balance))
            raise ParamsError('提现金额超出余额')
        uw.UWcash = Decimal(str(uw.UWcash)) - Decimal(str(data.get('cncashnum')))
        kw = {}
        if commision_for == ApplyFrom.supplizer.value:
            sa = SupplizerAccount.query.filter(
                SupplizerAccount.SUid == request.user.id, SupplizerAccount.isdelete == False).first()
            cn = CashNotes.create({
                'CNid': str(uuid.uuid1()),
                'USid': request.user.id,
                'CNbankName': sa.SAbankName,
                'CNbankDetail': sa.SAbankDetail,
                'CNcardNo': sa.SAcardNo,
                'CNcashNum': Decimal(str(data.get('cncashnum'))).quantize(Decimal('0.00')),
                'CNcardName': sa.SAcardName,
                'CommisionFor': commision_for
            })
            kw.setdefault('CNcompanyName', sa.SACompanyName)
            kw.setdefault('CNICIDcode', sa.SAICIDcode)
            kw.setdefault('CNaddress', sa.SAaddress)
            kw.setdefault('CNbankAccount', sa.SAbankAccount)

        else:
            user = User.query.filter(User.USid == request.user.id, User.isdelete == False).first()

            cn = CashNotes.create({
                'CNid': str(uuid.uuid1()),
                'USid': request.user.id,
                'CNbankName': data.get('cnbankname'),
                'CNbankDetail': data.get('cnbankdetail'),
                'CNcardNo': data.get('cncardno'),
                'CNcashNum': Decimal(str(data.get('cncashnum'))).quantize(Decimal('0.00')),
                'CNcardName': user.USrealname,
                'CommisionFor': commision_for
            })
        db.session.add(cn)
        db.session.flush()
        # 创建审批流

        self.create_approval('tocash', request.user.id, cn.CNid, commision_for, **kw)
        return Success('已成功提交提现申请， 我们将在3个工作日内完成审核，请及时关注您的账户余额')

    def get_bankname(self):
        """根据卡号获取银行信息"""
        data = parameter_required(('cncardno',))
        self.__check_card_num(data.get('cncardno'))
        return self._verify_cardnum(data.get('cncardno'))

    # todo 佣金配置文件修改接口

    @get_session
    @token_required
    def get_salesvolume_all(self):
        """获取团队销售额"""

        today = datetime.datetime.now()
        args = request.args.to_dict()
        month = args.get('month') or today.month
        year = args.get('year') or today.year

        if not is_shop_keeper():
            raise AuthorityError('权限不够')
        user = self.get_user_by_id(request.user.id)
        if user.USlevel != self.AGENT_TYPE:
            raise AuthorityError('代理商权限已过期')

        self._get_salesvolume(user, month, year)
        fens_list = [
            {
                'USheader': fens['USheader'],
                'USname': fens.USname,
                'USsalesvolume': fens.fens_amount
            } for fens in user.fens
        ]
        sub_list = [{
            'USheader': sub['USheader'],
            'USname': sub.USname,
            'USsalesvolume': float('%.2f' % (sub.team_sales))
        } for sub in user.subs]
        data = {
            'usvamout': float('%.2f' % (float(user.team_sales))),
            'fens_detail': fens_list,
            'sub_detail': sub_list,
        }
        return Success('获取收益详情成功', data=data)

    def _get_salesvolume(self, user, month, year, position=0, deeplen=3):
        user_total = 0
        user_fens_total = 0
        user_agent_total = 0
        user_usv = UserSalesVolume.query.filter(
            UserSalesVolume.USid == user.USid,
            extract('month', UserSalesVolume.createtime) == month,
            extract('year', UserSalesVolume.createtime) == year,
            UserSalesVolume.isdelete == False).first()
        user_fens_amount = Decimal(str(user_usv.USVamount)) if user_usv else 0
        user_agent_amount = Decimal(str(user_usv.USVamountagent)) if user_usv else 0
        if position >= deeplen:
            user.fill('team_sales', user_fens_amount)
            return
        position += 1

        fens_list = User.query.filter(
            User.isdelete == False, User.USsupper1 == user.USid, User.USlevel != self.AGENT_TYPE).all()
        sub_agent_list = User.query.filter(
            User.isdelete == False, User.USsupper1 == user.USid, User.USlevel == self.AGENT_TYPE).all()

        for fens in fens_list:
            usv = UserSalesVolume.query.filter(
                UserSalesVolume.USid == fens.USid,
                extract('month', UserSalesVolume.createtime) == month,
                extract('year', UserSalesVolume.createtime) == year,
                UserSalesVolume.isdelete == False).first()
            fens_amount = Decimal(str(usv.USVamount)) if usv else 0
            user_fens_total += fens_amount
            fens.fill('fens_amount', fens_amount)

        for sub_agent in sub_agent_list:

            self._get_salesvolume(sub_agent, month, year, position)

            user_agent_total += sub_agent.team_sales

        # 第一级不计算粉丝销售额
        if position == 1:
            user_total = user_agent_amount + user_fens_total + user_agent_total

        else:
            gennerc_log('user_agent_amount {} + user_fens_amount {} + user_fens_total {}+ user_agent_total {}'.format(user_agent_amount , user_fens_amount , user_fens_total , user_agent_total))
            user_total = user_agent_amount + user_fens_amount + user_fens_total + user_agent_total

        user.fill('team_sales', user_total)
        user.fill('fens', fens_list)
        user.fill('subs', sub_agent_list)

    @token_required
    def list_user_commison(self):
        """查看代理商获取的佣金列表"""
        data = parameter_required()
        mobile = data.get('mobile')
        name = data.get('name')
        level = data.get('level')
        usid = data.get('usid')
        user_query = User.query.filter(
            User.isdelete == False,
        )
        if level is None:  # 默认获取代理商
            user_query = user_query.filter(
                User.USlevel >= 2
            )
        elif level != 'all':  # 如果传all则获取全部
            user_query = user_query.filter(
                User.USlevel == int(level)
            )

        if mobile:
            user_query = user_query.filter(User.UStelphone.contains(mobile.strip()))
        if name:
            user_query = user_query.filter(User.USname.contains(name.strip()))
        if usid:
            user_query = user_query.filter(User.USid == usid)
        users = user_query.all_with_page()
        for user in users:
            # 佣金
            user.fields = ['USid', 'UStelphone', 'USname', 'USheader', 'USCommission1',
                           'USCommission2', 'USCommission3', 'USlevel']
            usid = user.USid

            wallet = UserWallet.query.filter(
                UserWallet.isdelete == False,
                UserWallet.USid == usid,
            ).first()
            remain = getattr(wallet, 'UWbalance', 0)
            total = getattr(wallet, 'UWtotal', 0)
            cash = getattr(wallet, 'UWcash', 0)
            user.fill('remain', remain)
            user.fill('total', total)
            user.fill('cash', cash)
            # 粉丝数
            fans_num = User.query.filter(
                User.isdelete == False,
                User.USsupper1 == usid,
            ).count()
            user.fill('fans_num', fans_num)
        return Success(data=users)

    @admin_required
    def list_fans(self):
        data = parameter_required(('usid', ))
        usid = data.get('usid')
        users = User.query.filter(
            User.isdelete == False,
            User.USsupper1 == usid
        ).all_with_page()
        for user in users:
            user.fields = self.USER_FIELDS[:]
            # 从该下级获得的佣金
            total = UserCommission.query.with_entities(func.sum(UserCommission.UCcommission)).\
                filter(
                    UserCommission.isdelete == False,
                    UserCommission.USid == usid,
                    UserCommission.FromUsid == user.USid,
                    UserCommission.UCstatus >= 0
            ).all()
            total = total[0][0] or 0
            user.fill('commision_from', total)
        return Success(data=users)

    @admin_required
    def update_user_commision(self):
        form = UpdateUserCommisionForm().valid_data()
        commision1 = form.commision1.data
        commision2 = form.commision2.data
        commision3 = form.commision3.data
        usid = form.usid.data
        with db.auto_commit():
            user = User.query.filter(
                User.isdelete == False,
                User.USid == usid
            ).first_('用户不存在')
            user.update({
                'USCommission1': commision1,
                'USCommission2': commision2,
                'USCommission3': commision3,
            }, 'dont ignore')
            db.session.add(user)
        return Success('设置成功')

    def __get_adnum(self):
        admin = Admin.query.order_by(Admin.ADnum.desc()).first()
        if not admin:
            return 100000
        return admin.ADnum + 1

    @token_required
    def get_cash_notes(self):
        cash_notes = CashNotes.query.filter_by_(USid=request.user.id).order_by(CashNotes.createtime.desc()).all_with_page()

        for cash_note in cash_notes:
            cash_note.fields = [
                'CNid',
                'createtime',
                'CNbankName',
                'CNbankDetail',
                'CNcardNo',
                'CNcardName',
                'CNcashNum',
                'CNstatus',
                'CNrejectReason',
            ]
            cash_note.fill('cnstatus', ApprovalAction(cash_note.CNstatus).zh_value)

        return Success('获取提现记录成功' ,data=cash_notes)

    @token_required
    def set_signin_default(self):
        if not is_admin():
            raise AuthorityError()
        data = request.json
        default_integral = str(data.get('integral'))
        if not re.match(r'^\d+$', default_integral):
            raise ParamsError('默认积分无效')
        default_rule = str(data.get('rule'))
        cfg = ConfigSettings()
        cfg.set_item('integralbase', 'integral', default_integral)
        cfg.set_item('integralrule', 'rule', default_rule)

        return Success('修改成功')

    def get_signin_default(self):
        if not is_admin():
            raise AuthorityError
        cfg = ConfigSettings()
        # sia_list = SignInAward.query.filter_by(isdelete=False).order_by(SignInAward.SIAday).all()
        # sia_rule = '\n'.join([sia.SIAnum for sia in sia_list])
        del_rule = cfg.get_item('integralrule', 'rule')
        del_integral = cfg.get_item('integralbase', 'integral')
        return Success('获取默认签到设置成功', data={'rule': del_rule, 'integral': del_integral})

    def _check_for_update(self, *args, **kwargs):
        """代理商是否可以升级"""
        pass

    @get_session
    @token_required
    def settlenment(self):
        """确认结算"""
        if not is_supplizer():
            raise AuthorityError('权限不足')
        today = datetime.datetime.now()
        data = request.json

        day = today.day
        if 1 < day < 22:
            raise TimeError('未到结算时间，每月22号之后可以结算')
        su = Supplizer.query.filter(Supplizer.SUid == request.user.id, Supplizer.isdelete == False).first()
        if not su:
            raise AuthorityError('账号已被回收')
        ssid = data.get('ssid')

        ss = SupplizerSettlement.query.filter(
            SupplizerSettlement.SSid == ssid, SupplizerSettlement.isdelete == False).first()
        if not ss:
            raise ParamsError('还在统计结算数据，晚点重试')
        if ss.SSstatus != SupplizerSettementStatus.settlementing.value:
            raise TimeError('结算处理中')

        action = data.get('action', ApplyStatus.agree.value)
        anabo = data.get('anabo')
        if int(action) == ApprovalAction.agree.value:
            ss.SSstatus = SupplizerSettementStatus.settlemented.value
            uw = UserWallet.query.filter(
                UserWallet.USid == su.SUid, UserWallet.isdelete == False,
                UserWallet.CommisionFor == ApplyFrom.supplizer.value).first()
            uw.UWbalance = Decimal(str(uw.UWbalance)) + Decimal((ss.SSdealamount))
            uw.UWcash = Decimal(str(uw.UWcash)) + Decimal(str(ss.SSdealamount))
            uw.UWtotal = Decimal(str(uw.UWtotal)) + Decimal(str(ss.SSdealamount))
            uw.UWexpect = Decimal(str(uw.UWexpect)) - Decimal(str(ss.SSdealamount))
        else:
            ss.SSstatus = SupplizerSettementStatus.approvaling.value
            ssa = SettlenmentApply.create({
                'SSAid': str(uuid.uuid1()),
                'SUid': su.SUid,
                'SSid': ss.SSid,
                'SSAabo': anabo
            })
            db.session.add(ssa)
            db.session.flush()

            self.create_approval('tosettlenment', su.SUid, ssa.SSAid)

        return Success('结算处理')

    @get_session
    @token_required
    def create_settlenment(self):
        today = datetime.datetime.now()
        su_comiission_list = UserCommission.query.filter(
            UserCommission.USid == request.user.id,
            UserCommission.isdelete == False,
            UserCommission.UCstatus == UserCommissionStatus.in_account.value,
            UserCommission.CommisionFor == ApplyFrom.supplizer.value,
            extract('month', UserCommission.createtime) == today.month,
            extract('year', UserCommission.createtime) == today.year
        ).all()
        ss_total = sum(Decimal(str(su.UCcommission)) or 0 for su in su_comiission_list)

        ss = SupplizerSettlement.create({
            'SSid': str(uuid.uuid1()),
            'SUid': request.user.id,
            'SSdealamount': float('%.2f' %float(ss_total)),
            'SSstatus': SupplizerSettementStatus.settlementing.value
        })
        db.session.add(ss)
        return Success('创建结算记录成功')

    @token_required
    def get_settlenment(self):
        # if not is_supplizer():
        #     raise AuthorityError('')
        su = Supplizer.query.filter(
            Supplizer.SUid == request.user.id, Supplizer.isdelete == False).first_('账号已回收')
        ss_list = SupplizerSettlement.query.filter(
            SupplizerSettlement.SUid == request.user.id,
            SupplizerSettlement.isdelete == False
        ).all()

        for ss in ss_list:
            ss.fill('ssstatus', SupplizerSettementStatus(ss.SSstatus).zh_value)
            ss.fill('suname', su.SUname)
            ss.add('createtime')
        return Success('获取结算记录成功', data=ss_list)

