# -*- coding: utf-8 -*-
from flask import current_app

from planet.config.enums import ProductStatus, ItemType
from planet.models import ProductBrand, Supplizer
from .base_form import *
from datetime import datetime


class BrandsListForm(BaseForm):
    index = SelectField('是否展示在首页', choices=[('false', False), ('true', True), ('null', None)], default='null')
    time_order = SelectField('排序方式',
                             choices=[('desc', ProductBrand.createtime.desc()),
                                      ('asc', ProductBrand.createtime)],
                             default='desc')
    pbstatus = SelectField('状态', choices=[('upper', 0), ('off_shelves', 10), ('all', None)], default='upper')
    itid = StringField('品牌标签id')
    free = SelectField(choices=[('false', False), ('true', True), ('all', 'all')], default='all')
    kw = StringField()


class BrandsCreateForm(BaseForm):
    pblogo = StringField(validators=[DataRequired('logo不可为空'), Length(1, 255)])
    pbname = StringField(validators=[DataRequired('名字不可为空'), Length(1, 32)])
    pbdesc = StringField(validators=[Length(1, 255)])
    pblinks = StringField()
    itids = FieldList(StringField(), validators=[DataRequired('需指定标签')])
    suid = StringField()
    pbbackgroud = StringField(validators=[Length(1, 255)])
    pbintegralpayrate = IntegerField('允许星币抵扣的百分数的分子')
    pbsort = IntegerField('权重')

    def validate_suid(self, raw):
        if raw.data:
            Supplizer.query.filter(
                Supplizer.isdelete == False,
                Supplizer.SUid == raw.data
            ).first_('不存在的供应商')

    def validate_pbintegralpayrate(self, raw):
        if raw.data and not 0 < raw.data <= 100:
            raise ParamsError("请输入正确的星币抵扣百分比(0 - 100)%")


class BrandUpdateForm(BrandsCreateForm):
    pbid = StringField(validators=[DataRequired('需指定品牌'), Length(1, 64)])


class ProductOffshelvesForm(BaseForm):
    prid = StringField(validators=[DataRequired('需指定商品')])
    status = IntegerField()

    def validate_status(self, value):
        try:
            if value.data in [ProductStatus.all.value, ProductStatus.auditing.value, None]:
                raise Exception
            ProductStatus(value.data)
        except Exception as e:
            raise ValidationError(message='状态筛选有误')
        self.status = value


class ProductOffshelvesListForm(BaseForm):
    prids = FieldList(StringField(), validators=[DataRequired('需要指定商品')])
    status = IntegerField()

    def validate_status(self, value):
        try:
            if value.data in [ProductStatus.all.value, ProductStatus.auditing.value, None]:
                raise Exception
            ProductStatus(value.data)
        except Exception as e:
            raise ValidationError(message='状态错误')
        self.status = value


class ProductApplyAgreeForm(BaseForm):
    """商品同意或拒绝"""
    prids = FieldList(StringField(), validators=[DataRequired('需指定商品')])
    agree = BooleanField()
    anabo = StringField()


class SceneListForm(BaseForm):
    kw = StringField(default='')


class SceneCreateForm(BaseForm):
    """场景创建"""
    pspic = StringField('图片', validators=[DataRequired('图片不可为空'), Length(0, 255)])
    psname = StringField('名字', validators=[DataRequired('名字不可为空'), Length(0, 16)])
    pssort = IntegerField('排序')
    pstimelimited = BooleanField('是否限时', default=False)
    psstarttime = DateTimeField('限时开始时间')
    psendtime = DateTimeField('限时结束时间')

    def validate_pstimelimited(self, value):
        if value.data:
            if not (self.psstarttime.data or self.psendtime.data):
                raise ValidationError(message='限时场景必须设置开始与结束时间')
            else:
                if self.psendtime.data < datetime.now():
                    raise ValidationError(message='限时场景结束时间不能小于当前时间')
                elif self.psendtime.data < self.psstarttime.data:
                    raise ValidationError(message='限时场景结束时间不能小于开始时间')
        else:
            self.psstarttime.data = None
            self.psendtime.data = None


class SceneUpdateForm(SceneCreateForm):
    psid = StringField(validators=[DataRequired('需要指定场景')])
    pspic = StringField('图片')
    psname = StringField('场景名')
    pssort = IntegerField('排序')
    isdelete = BooleanField(default=False)


