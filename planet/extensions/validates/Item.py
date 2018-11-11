# -*- coding: utf-8 -*-
from wtforms.validators import *
from wtforms import *

from planet.config.enums import ItemType
from .base_form import BaseForm


class ItemListForm(BaseForm):
    ittype = IntegerField()
    psid = StringField()


class ItemCreateForm(BaseForm):
    """创建标签"""
    psid = StringField('场景id')
    itname = StringField('标签名字', validators=[DataRequired()])
    itsort = IntegerField()
    itdesc = StringField()
    ittype = IntegerField(default=ItemType.product.value)

    def validate_ittype(self, raw):
        try:
            ItemType(raw.data)
        except Exception as e:
            raise ValidationError(message='ittype未找到对应的类型')
        # 如果类型为商品的标签, 则必需传场景id
        if raw.data == ItemType.product.value and not self.psid.data:
            raise ValidationError(message='商品标签必需对应场景')
        if raw.data != ItemType.product.value and self.psid.data:
            raise ValidationError(message='非商品标签无需对应场景')
        self.ittype = raw
