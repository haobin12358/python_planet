# -*- coding: utf-8 -*-
from datetime import date

from sqlalchemy import cast, Date

from planet.common.error_response import StatusError, DumpliError
from planet.models.activity import GuessNum, Activity
from .base_form import *


class ActivityUpdateForm(BaseForm):
    actype = IntegerField(validators=[InputRequired('请输入活动类型')])
    acbackground = StringField('背景图')
    actoppic = StringField('顶部图')
    acbutton = StringField('按钮')
    acdesc = StringField('活动')
    acname = StringField('名字')
    acsort = IntegerField('顺序标志')
    acshow = BooleanField('是否显示')

    def validate_actype(self, raw):
        activiy = Activity.query.filter_by_({'ACtype': raw.data}).first_('活动不存在')
        self.activity = activiy


class ActivityGetForm(BaseForm):
    actype = IntegerField(validators=[InputRequired('请输入活动类型')])
    mbaid = StringField()
    usid_base = StringField()

    def validate_actype(self, raw):
        activiy = Activity.query.filter_by_({'ACtype': raw.data}).first_('活动不存在')
        self.activity = activiy



class GuessNumCreateForm(BaseForm):
    gnnum = StringField('猜测的数字', validators=[DataRequired('请输入数字')])

    def validate_gnnum(self, raw):
        try:
            float(raw.data)
        except ValueError:
            raise ParamsError('数字格式不正确')
        is_exists = GuessNum.query.filter(
            GuessNum.USid == request.user.id,
            GuessNum.isdelete == False,
            cast(GuessNum.createtime, Date) == date.today(),
        ).first()
        if is_exists:
            raise DumpliError('今日已参与')


class GuessNumGetForm(BaseForm):
    date = StringField('日期', default='today')

    def validate_date(self, raw):
        if raw.data == 'today':
            raw.data = date.today()
        else:
            try:
                raw.data = datetime.datetime.strptime(raw.data, '%Y%m%d')
            except ValueError as e:
                raise ParamsError('请输入正确的日期')


class GuessNumHistoryForm(BaseForm):
    year = StringField('年')
    month = StringField('月')

    def validate_year(self, raw):
        if not raw.data:
            raw.data = str(date.today().year)

    def validate_month(self, raw):
        if not raw.data:
            raw.data = str(date.today().month)


class MagicBoxOpenForm(BaseForm):
    level = SelectField(choices=[("1", 'Gearsone'),
                                 ('2', 'Gearstwo'),
                                 ('3', 'Gearsthree')])

    usid_base = StringField()
    mbaid = StringField('进行中的活动')


class MagicBoxCreateForm(BaseForm):
    mbaid = StringField('当前活动的唯一标志', validators=[DataRequired('需要传入 mbaid')])





