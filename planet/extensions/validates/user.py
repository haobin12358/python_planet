from planet.common.error_response import DumpliError
from planet.models import Supplizer
from .base_form import *


class SupplizerLoginForm(BaseForm):
    mobile = StringField('手机号', validators=[DataRequired('手机号不可以为空')])
    password = StringField('密码', validators=[DataRequired('密码不可为空')])


class SupplizerListForm(BaseForm):
    kw = StringField('关键词', default='')
    mobile = StringField('手机号', default='')


class SupplizerCreateForm(BaseForm):
    sulinkphone = StringField('联系电话', validators=[
        DataRequired('手机号不可以为空'),
        Regexp('^1{10}$', message='手机号格式错误'),
    ])
    suname = StringField('供应商名字')
    sulinkman = StringField('联系人', validators=[DataRequired('联系人不可为空')])
    suaddress = StringField('地址', validators=[DataRequired('地址不可以为空')])
    subanksn = StringField('卡号')
    subankname = StringField('银行名字')
    supassword = StringField('密码', validators=[DataRequired('密码不可为空')])
    suheader = StringField('头像')
    sucontract = FieldList(StringField())

    def validate_sulinkphone(self, raw):
        is_exists = Supplizer.query.filter_by_().filter_(
            Supplizer.SUlinkPhone == raw.data
        ).first()
        if is_exists:
            raise DumpliError('已存在')
