from .base_form import *


class UserWordsCreateForm(BaseForm):
    uwtelphone = StringField('留言人手机号', validators=[
        DataRequired('手机号不可以为空'),
        Regexp('^1\d{10}$', message='手机号格式错误'),
    ])
    uwmessage = StringField("留言内容", validators=[DataRequired("留言内容不得为空")])
    uwname = StringField("留言人姓名")
    uwemail = StringField("留言人邮箱", validators=[Regexp(r'^\w+@(\w+\.)+(com|cn|net)$', message="邮箱格式错误")])


class CompanyMessageForm(BaseForm):
    cmtitle = StringField("公告标题", validators=[DataRequired("公告标题不得为空")])
    cmmessage = StringField("公告详情", validators=[DataRequired("公告内容不得为空")])
    cmindex = IntegerField("公告是否展示到首页")
