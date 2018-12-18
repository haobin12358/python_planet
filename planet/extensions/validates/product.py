# -*- coding: utf-8 -*-
from planet.config.enums import ProductStatus, ItemType
from planet.models import ProductBrand
from .base_form import *


class BrandsListForm(BaseForm):
    index = SelectField('是否展示在首页', choices=[('false', False), ('true', True), ('null', None)], default='null')
    time_order = SelectField('排序方式',
                             choices=[('desc', ProductBrand.createtime.desc()),
                                      ('asc', ProductBrand.createtime)],
                             default='desc')
    pbstatus = SelectField('状态', choices=[('upper', 0), ('off_shelves', 10), ('all', None)], default='upper')
    itid = StringField('品牌标签id')


class BrandsCreateForm(BaseForm):
    pblogo = StringField(validators=[DataRequired('logo不可为空'), Length(1, 255)])
    pbname = StringField(validators=[DataRequired('名字不可为空'), Length(1, 32)])
    pbdesc = StringField(validators=[Length(1, 255)])
    pblinks = StringField()
    itids = FieldList(StringField(), validators=[DataRequired('itid不可为空')])
    pbbackgroud = StringField(validators=[Length(1, 255)])



class BrandUpdateForm(BaseForm):
    pbid = StringField(validators=[DataRequired('bpid不可为空'), Length(1, 64)])
    pblogo = StringField()
    pbname = StringField()
    pbdesc = StringField()
    pblinks = StringField()
    itids = FieldList(StringField(), validators=[DataRequired('itid不可为空')])


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


class ProductOffshelvesListForm(BaseForm):
    prids = FieldList(StringField(), validators=[DataRequired('prid不可为空')])
    status = IntegerField()

    def validate_status(self, value):
        try:
            if value.data in [ProductStatus.all.value, ProductStatus.auditing.value, None]:
                raise Exception
            ProductStatus(value.data)
        except Exception as e:
            raise ValidationError(message='status 参数错误')
        self.status = value


class ProductApplyAgreeForm(BaseForm):
    """商品同意或拒绝"""
    prids = FieldList(StringField(), validators=[DataRequired('prids不可为空')])
    agree = BooleanField()
    anabo = StringField()


class SceneCreateForm(BaseForm):
    """场景创建"""
    pspic = StringField('图片', validators=[DataRequired('图片不可为空'), Length(0, 255)])
    psname = StringField('名字', validators=[DataRequired('名字不可为空'), Length(0, 16)])
    pssort = IntegerField('排序')




