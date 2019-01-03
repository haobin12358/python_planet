# -*- coding: utf-8 -*-
from .base_form import *


class IndexListBannerForm(BaseForm):
    ibshow = SelectField('是否显示', choices=[('false', False), ('true', True), ('all', None)], default='true')


class IndexSetBannerForm(BaseForm):
    ibpic = StringField('图片', validators=[DataRequired('图片不可为空')])
    ibsort = IntegerField('顺序')
    ibshow = BooleanField('是否显示')
    isdelete = BooleanField('是否删除')
    contentlink = StringField('跳转链接', validators=[DataRequired('跳转链接不可为空')])


class IndexUpdateBannerForm(BaseForm):
    ibid = StringField('轮播id', validators=[DataRequired('ibid不能为空')])
    contentlink = StringField('跳转链接')
    ibpic = StringField('图片')
    ibsort = IntegerField('顺序')
    ibshow = BooleanField('是否显示')
    isdelete = BooleanField('是否删除')

    def validate_contentlink(self, raw):
        if raw.data is None and self.isdelete.data is None:
            raise ValidationError('跳转链接不可为空')