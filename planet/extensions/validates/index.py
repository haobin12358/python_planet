# -*- coding: utf-8 -*-
from .base_form import *


class IndexListBannerForm(BaseForm):
    ibshow = SelectField('是否显示', choices=[('false', False), ('true', True), ('all', None)], default='true')


class IndexSetHotForm(BaseForm):
    prid = StringField('商品id')
