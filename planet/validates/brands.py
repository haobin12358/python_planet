# -*- coding: utf-8 -*-
from wtforms.validators import *
from wtforms import *

from planet.models import ProductBrand
from .base_form import BaseForm


class BrandsListForm(BaseForm):
    index = SelectField('是否展示在首页', choices=[('false', False), ('true', True), ('null', None)], default='null')
    time_order = SelectField('排序方式',
                             choices=[('desc', ProductBrand.createtime.desc()),
                                      ('asc', ProductBrand.createtime)],
                             default='desc')
    pbstatus = SelectField('状态', choices=[('upper', 0), ('off_shelves', 10), ('all', None)], default='upper')


class BrandsCreateForm(BaseForm):
    pblogo = StringField(validators=[DataRequired(), Length(1, 255)])
    pbname = StringField(validators=[DataRequired(), Length(1, 255)])
    pbdesc = StringField(validators=[Length(1, 255)])
    pblinks = StringField(validators=[Length(1, 255)])

