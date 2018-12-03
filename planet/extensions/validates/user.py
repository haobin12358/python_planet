from planet.common.error_response import NotFound
from planet.models import Supplizer
from .base_form import *


class SupplizerLoginForm(BaseForm):
    mobile = StringField('手机号', validators=[DataRequired('手机号不可以为空')])
    password = StringField('密码', validators=[DataRequired('密码不可为空')])
