# -*- coding: utf-8 -*-
from wtforms.validators import *
from wtforms import *

from planet.config.enums import ProductStatus, ItemType
from planet.models import ProductBrand
from .base_form import BaseForm


class BrandsListForm(BaseForm):
    index = SelectField('是否展示在首页', choices=[('false', False), ('true', True), ('null', None)], default='null')
    time_order = SelectField('排序方式',
                             choices=[('desc', ProductBrand.createtime.desc()),
                                      ('asc', ProductBrand.createtime)],
                             default='desc')
    pbstatus = SelectField('状态', choices=[('upper', 0), ('off_shelves', 10), ('all', None)], default='upper')
    itid = StringField('品牌标签id')


class BrandsCreateForm(BaseForm):
    pblogo = StringField(validators=[DataRequired(), Length(1, 255)])
    pbname = StringField(validators=[DataRequired(), Length(1, 32)])
    pbdesc = StringField(validators=[Length(1, 255)])
    pblinks = StringField(validators=[Length(1, 255)])
    itids = StringField('品牌标签id', validators=[])


class BrandUpdateForm(BaseForm):
    pbid = StringField(validators=[DataRequired(), Length(1, 64)])
    pblogo = StringField(validators=[Length(1, 255)])
    pbname = StringField(validators=[Length(1, 32)])
    pbdesc = StringField(validators=[Length(1, 255)])
    pblinks = StringField(validators=[Length(1, 255)])
    itids = StringField('品牌标签id', validators=[DataRequired()])


class ProductOffshelvesForm(BaseForm):
    prid = StringField(validators=[DataRequired('prid不可以为空')])
    status = IntegerField()

    def validate_status(self, value):
        try:
            if value.data in [ProductStatus.all.value, ProductStatus.auditing.value, None]:
                raise Exception
            ProductStatus(value.data)
        except Exception as e:
            raise ValidationError(message='status 参数错误')
        self.status = value


class SceneCreateForm(BaseForm):
    """场景创建"""
    pspic = StringField('图片', validators=[DataRequired(), Length(0, 255)])
    psname = StringField('名字', validators=[DataRequired(), Length(0, 16)])
    pssort = IntegerField('排序')



