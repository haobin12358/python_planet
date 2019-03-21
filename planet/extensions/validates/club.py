import re

from planet.common.error_response import DumpliError, ParamsError
from planet.common.token_handler import is_supplizer
from planet.models import Supplizer
from .base_form import *

class UserWordsCreateForm(BaseForm):
    UWtelphone = StringField('留言人手机号', validators=[
        DataRequired('手机号不可以为空'),
        Regexp('^1\d{10}$', message='手机号格式错误'),
    ])
    UWmessage = StringField("留言内容", validators=[DataRequired("留言内容不得为空")])
    UWname = StringField("留言人姓名")
    UWemail = StringField("留言人邮箱")