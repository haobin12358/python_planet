# -*- coding: utf-8 -*-
from wtforms.ext.sqlalchemy.orm import model_form

from planet.common.error_response import AuthorityError, StatusError
from planet.common.token_handler import is_admin, is_supplizer
from planet.config.enums import OrderMainStatus, OrderRefundOrstatus
from planet.models import Products, ProductBrand, ProductCategory
from planet.models.trade import OrderMain, Coupon, OrderRefund, LogisticsCompnay
from .base_form import *


class OrderListForm(BaseForm):
    omstatus = Field('状态')
    issaler = BooleanField('卖家版', default=False)
    usid = StringField('用户id')
    extentions = StringField('一些扩展的查询')
    omfrom = StringField('来源')
    ordertype = StringField('区分活动订单')
    omno = StringField('订单编号')
    omrecvname = StringField('收件人')
    omrecvphone = StringField('收件手机号码')
    prtitle = StringField('商品名')
    createtime_start = DateField('开始时间')
    createtime_end = DateField('结束时间')
    orastatus = IntegerField('审核处理状态')
    orstatus = IntegerField('售后物流处理状态')
    paytime_start = DateField('付款开始时间')
    paytime_end = DateField('付款结束时间')
    export_xls = BooleanField('是否导出')

    def validate_omstatus(self, raw):
        try:
            if raw.data is None:
                self.omstatus.data = []
            else:
                raw.data = int(raw.data)
                OrderMainStatus(raw.data)
                self.omstatus.data = [
                    OrderMain.OMstatus == raw.data,
                    OrderMain.OMinRefund == False
                ]
        except ValueError as e:
            if raw.data in ['inrefund', 'refund', 40, '40']:
                self.omstatus.data = 'refund'  # 标志一下, 需要查售后中的订单
            #     self.omstatus.data = [
            #         OrderMain.OMinRefund == True,
            #     ]
            # else:
            #     raise ValidationError('status 参数错误')
        except Exception as e:
            raise e

    def validate_usid(self, raw):
        if not is_admin() and not is_supplizer():  # 非管理员, 不可以制定他人usid
            self.usid.data = request.user.id

    def validate_omfrom(self, raw):
        if raw.data:
            raw.data = list(map(int, raw.data.split(',')))

    def validate_issaler(self, raw):
        """是否卖家"""
        if raw.data is True:
            pass


class CouponUserListForm(BaseForm):
    """用户优惠券"""
    usid = StringField('用户id', default=None)
    itid = StringField('标签id')
    ucalreadyuse = SelectField('是否已经使用', choices=[
        ('true', True), ('false', False), ('all', None)
    ], default='false')
    canuse = SelectField('是否已经使用', choices=[
        ('true', True), ('false', False), ('all', None)
    ], default='all')

    def validate_usid(self, raw):
        """普通用户默认使用自己的id"""
        if not raw.data:
            if not is_admin():
                raw.data = request.user.id
                if request.user.id != raw.data:
                    raise AuthorityError()


class CouponListForm(BaseForm):
    """优惠券"""
    itid = StringField('标签id')


class CouponFetchForm(BaseForm):
    coid = StringField('优惠券id', validators=[DataRequired('请选择优惠券')])


class CouponCreateForm(BaseForm):
    """创建优惠券"""
    pcids = FieldList(StringField())
    prids = FieldList(StringField())
    pbids = FieldList(StringField())
    coname = StringField(validators=[DataRequired('请输入优惠券名字'), Length(1, 32)])
    coisavailable = BooleanField('可用', default=True)
    coiscancollect = BooleanField('可以领取', default=True)
    colimitnum = IntegerField('发放数量', default=0, validators=[NumberRange(0)])
    cocollectnum = IntegerField('限领数量', default=0, validators=[NumberRange(0)])
    cosendstarttime = DateTimeField('抢券时间起', default=datetime.datetime.now)
    cosendendtime = DateTimeField('抢卷时间止')
    covalidstarttime = DateTimeField('有效时间起')
    covalidendtime = DateTimeField('有效时间起')
    codiscount = FloatField('折扣', default=10, validators=[NumberRange(0, 10)])
    codownline = FloatField('满额可用', default=0, validators=[NumberRange(0)])
    cosubtration = FloatField('减额', default=0, validators=[NumberRange(0)])
    codesc = StringField('描述')
    itids = FieldList(StringField(), validators=[DataRequired('请指定所在标签')])
    cousenum = IntegerField('可叠加使用数量', default=1)
    cocode = BooleanField('是否需要兑换码', default=False)

    def valid_data(self):
        if self.prids.data and self.pbids.data:
            raise ValidationError('不可以同时指定品牌和商品')
        for prid in self.prids.data:
            product = Products.query.filter_by_({"PRid": prid}).first_('商品不存在')
        for pbid in self.pbids.data:
            brand = ProductBrand.query.filter_by_({"PBid": pbid}).first_('品牌不存在')
        return super(CouponCreateForm, self).valid_data()

    def validate_cosubtration(self, raw):
        """减额或打折必需存在一个"""
        if not raw.data and self.codiscount.data == 10:
            raise ValidationError('减额或打折必需存在一个')
        if raw.data and self.codiscount.data != 10:
            raise ValidationError('减额或打折必需存在一个')

    def validate_cousenum(self, raw):
        if raw.data < 0:
            raise ValidationError('可叠加数量错误')


class CouponUpdateForm(CouponCreateForm):
    """更新优惠券"""
    coid = StringField('优惠券id', validators=[DataRequired('需指定优惠券')])


class RefundSendForm(BaseForm):
    oraid = StringField('售后申请单id', validators=[DataRequired('需指定申请单')])
    orlogisticcompany = StringField('物流公司编码', validators=[DataRequired('物流公司不可为空')])
    orlogisticsn = StringField('物流单号', validators=[DataRequired('单号不可为空'), Length(8, 64, message='单号长度不符规范')])


class RefundConfirmForm(BaseForm):
    oraid = StringField(validators=[DataRequired('需指定申请单')])
    agree = BooleanField()


class RefundConfirmRecvForm(BaseForm):
    oraid = StringField(validators=[DataRequired('需指定申请单')])


class HistoryDetailForm(BaseForm):
    days = StringField()


class ActRuleSetFrom(BaseForm):
    acrrule = StringField()
    acrphone = StringField()
    acraddress = StringField()
    acrname = StringField(validators=[DataRequired('姓名不可为空')])
    acrbanksn = StringField(validators=[DataRequired('卡号不可为空')])
    acrbankaddress = StringField()
    acrnum = IntegerField()
    acrcash = DecimalField()




