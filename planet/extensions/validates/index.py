# -*- coding: utf-8 -*-
from wtforms.validators import *
from wtforms import *

from .base_form import BaseForm


class IndexListBannerForm(BaseForm):
    ibshow = SelectField('是否显示', choices=[('false', False), ('true', True), ('all', None)], default='true')
