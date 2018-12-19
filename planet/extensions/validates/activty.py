# -*- coding: utf-8 -*-
from datetime import date

from sqlalchemy import cast, Date

from planet.common.error_response import StatusError, DumpliError
from planet.config.enums import Client, ActivityRecvStatus, PayType
from planet.extensions.register_ext import db
from planet.models import AddressArea, AddressCity, AddressProvince, UserAddress
from planet.models.activity import GuessNum, Activity, MagicBoxJoin
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
    mbjid = StringField('参与活动的唯一标志')

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
            self.date.data = datetime.datetime.today()
        else:
            try:
                self.date.data = datetime.datetime.strptime(raw.data, '%Y%m%d')
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
    mbaid = StringField('进行中的活动')
    mbjid = StringField('参与记录来源')


class MagicBoxJoinForm(BaseForm):
    mbaid = StringField('当前活动的唯一标志', validators=[DataRequired('需要传入 mbaid')])


class MagicBoxRecvAwardForm(BaseForm):
    # mbjid = StringField('参与记录id', validators=[DataRequired('传入参与记录id')])
    uaid = StringField('地址id', validators=[DataRequired('地址不可为空')])
    omclient = IntegerField('下单设备', default=Client.wechat.value)
    ommessage = StringField('留言')
    opaytype = IntegerField('支付类型')
    mbaid = StringField('活动唯一标志', validators=[DataRequired('mbaid不可为空')])

    # def validate_mbjid(self, raw):
    #     self.magic_box_join = MagicBoxJoin.query.filter_by_({'MBJid': raw.data}).first_('未参与活动')
    #     if self.magic_box_join.MBJstatus != ActivityRecvStatus.wait_recv.value:
    #         raise StatusError('已领奖或已过期')

    def validate_omclient(self, raw):
        Client(raw.data)

    def validate_opaytype(self, raw):
        PayType(raw.data)



