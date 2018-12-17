# -*- coding: utf-8 -*-
from .base_form import *


class IndexListBannerForm(BaseForm):
    ibshow = SelectField('是否显示', choices=[('false', False), ('true', True), ('all', None)], default='true')


class IndexSetBannerForm(BaseForm):
    prid = StringField('商品id')
    ibpic = StringField('图片', validators=[DataRequired('图片不可为空')])
    ibsort = IntegerField('顺序')
    ibshow = BooleanField('是否显示')
    isdelete = BooleanField('是否删除')


class IndexUpdateBannerForm(BaseForm):
    ibid = StringField('轮播id', validators=[DataRequired('ibid不能为空')])
    prid = StringField('商品id')
    ibpic = StringField('图片')
    ibsort = IntegerField('顺序')
    ibshow = BooleanField('是否显示')
    isdelete = BooleanField('是否删除')
