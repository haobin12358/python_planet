import re

from planet.common.error_response import DumpliError, ParamsError
from planet.common.token_handler import is_supplizer
from planet.models import Supplizer
from .base_form import *


class SupplizerLoginForm(BaseForm):
    mobile = StringField('手机号', validators=[DataRequired('手机号不可以为空')])
    password = StringField('密码', validators=[DataRequired('密码不可为空')])


class SupplizerListForm(BaseForm):
    kw = StringField('关键词', default='')
    mobile = StringField('手机号', default='')


class SupplizerGetForm(BaseForm):
    suid = StringField()

    def validate_suid(self, raw):
        if is_supplizer():
            self.suid.data = request.user.id
        else:
            if not raw.data:
                raise ParamsError('供应商suid不可为空')
        supplizer= Supplizer.query.filter(Supplizer.SUid == raw.data,
                                           Supplizer.isdelete == False).first_('供应商不存在')
        self.supplizer = supplizer


class SupplizerCreateForm(BaseForm):
    suloginphone = StringField('登录手机号', validators=[
        DataRequired('手机号不可以为空'),
        Regexp('^1\d{10}$', message='手机号格式错误'),
    ])
    sulinkphone = StringField('联系电话')
    suname = StringField('供应商名字')
    sulinkman = StringField('联系人', validators=[DataRequired('联系人不可为空')])
    suaddress = StringField('地址', validators=[DataRequired('地址不可以为空')])
    subanksn = StringField('卡号')
    subankname = StringField('银行名字')
    supassword = StringField('密码', validators=[DataRequired('密码不可为空')])
    suheader = StringField('头像')
    sucontract = FieldList(StringField(validators=[DataRequired('合同列表不可以为空')]))
    pbids = FieldList(StringField('品牌'))
    subusinesslicense = StringField('营业执照')
    suregisteredfund = StringField('注册资金',)
    sumaincategory = StringField('主营类目', )
    suregisteredtime = DateField('注册时间',)
    sulegalperson = StringField('法人',)
    suemail = StringField('联系邮箱', )
    sulegalpersonidcardfront = StringField('法人身份证正面', )
    sulegalpersonidcardback = StringField('法人身份证反面', )

    def validate_suloginphone(self, raw):
        is_exists = Supplizer.query.filter_by_().filter_(
            Supplizer.SUloginPhone == raw.data, Supplizer.isdelete == False
        ).first()
        if is_exists:
            raise DumpliError('登陆手机号已存在')

    def validate_sulinkphone(self, raw):
        if raw.data:
            if not re.match('^1\d{10}$', raw.data):
                raise ParamsError('联系人手机号格'
                                  '式错误')
    def validate_suemail(self, raw):
        if raw.data:
            if not re.match(r'^[A-Za-z\d]+([-_.][A-Za-z\d]+)*@([A-Za-z\d]+[-.])+[A-Za-z\d]{2,4}$', raw.data):
                raise ParamsError('联系邮箱格式错误')

class SupplizerUpdateForm(BaseForm):
    suid = StringField()
    sulinkphone = StringField('联系电话')
    suname = StringField('供应商名字')
    sulinkman = StringField('联系人', validators=[DataRequired('联系人不可为空')])
    suaddress = StringField('地址', validators=[DataRequired('地址不可以为空')])
    subanksn = StringField('卡号')
    subankname = StringField('银行名字')
    suheader = StringField('头像')
    sucontract = FieldList(StringField(validators=[DataRequired('合同列表不可以为空')]))
    suemail = StringField('邮箱')
    pbids = FieldList(StringField('品牌'))

    def validate_suid(self, raw):
        if is_supplizer():
            self.suid.data = request.user.id
        else:
            if not raw.data:
                raise ParamsError('供应商suid不可为空')

    def validate_sulinkphone(self, raw):
        if raw.data:
            if not re.match('^1\d{10}$', raw.data):
                raise ParamsError('联系人手机号格'
                                  '式错误')



class SupplizerSendCodeForm(BaseForm):
    suloginphone = StringField('登录手机号', validators=[
        DataRequired('手机号不可以为空'),
        Regexp('^1\d{10}$', message='手机号格式错误'),
    ])


class SupplizerResetPasswordForm(BaseForm):
    suloginphone = StringField('登录手机号', validators=[
        DataRequired('手机号不可以为空'),
        Regexp('^1\d{10}$', message='手机号格式错误'),
    ])
    suid = StringField('供应商id')
    code = StringField('验证码')
    supassword = StringField(validators=[DataRequired('验证码不可为空')])

    def validate_suid(self, raw):
        if is_supplizer():
            self.suid.data = request.user.id


class SupplizerChangePasswordForm(BaseForm):
    suid = StringField('供应商id')
    supassword = StringField(validators=[DataRequired('验证码不可为空')])
    oldpassword = StringField('旧密码')

    def validate_suid(self, raw):
        if is_supplizer():
            self.suid.data = request.user.id


class UpdateUserCommisionForm(BaseForm):
    usid = StringField(validators=[DataRequired('用户id不可为空')])
    commision1 = DecimalField()
    commision2 = DecimalField()
    commision3 = DecimalField()

    def validate_commision1(self, raw):
        if raw.data and (raw.data < 0 or raw.data > 100):
            raise ParamsError('一级佣金设置不合理')

    def validate_commision2(self, raw):
        if raw.data and (raw.data < 0 or raw.data > 100):
            raise ParamsError('二级佣金设置不合理')

    def validate_commision3(self, raw):
        if raw.data and (raw.data < 0 or raw.data > 100):
            raise ParamsError('三级佣金设置不合理')
