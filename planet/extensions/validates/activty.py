# -*- coding: utf-8 -*-
from datetime import date

from sqlalchemy import cast, Date

from planet.common.error_response import StatusError, DumpliError
from planet.models.activity import GuessNum
from .base_form import *


class ActivityUpdateForm(BaseForm):
    acid = StringField(validators=[DataRequired('请输入活动id')])



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




