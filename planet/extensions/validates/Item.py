# -*- coding: utf-8 -*-
from planet.config.enums import ItemType, ItemAuthrity, ItemAuthrity, ItemPostion
from .base_form import *


class ItemListForm(BaseForm):
    ittype = IntegerField()
    psid = StringField()
    recommend = IntegerField()
    itauthority = IntegerField(default=ItemAuthrity.no_limit.value)  # 查看权限
    itposition = IntegerField(default=ItemPostion.scene.value)  # 标签位置

    def validate_psid(self, raw):
        if raw.data and self.ittype.data is not None:
            if self.ittype.data != ItemType.product.value:
                raise ValidationError('仅商品标签可以筛选场景id')
        if raw.data and self.ittype.data is None:
            self.ittype.data = ItemType.product.value

    def validate_recommend(self, raw):
        if raw.data and self.ittype.data is not None:
            if self.ittype.data != ItemType.news.value:
                raise ValidationError('仅资讯标签可筛选推荐类型')
        if raw.data and self.ittype.data is None:
            self.ittype.data = ItemType.news.value


class ItemCreateForm(BaseForm):
    """创建标签"""
    psid = StringField('场景id')
    itname = StringField('标签名字', validators=[DataRequired('itname不可为空')])
    itsort = IntegerField()
    itdesc = StringField()
    ittype = IntegerField(default=ItemType.product.value)
    itauthority = IntegerField()

    def validate_ittype(self, raw):
        try:
            ItemType(raw.data)
        except Exception as e:
            raise ValidationError(message='ittype未找到对应的类型')
        # 如果类型为商品的标签, 则必需传场景id
        # if raw.data == ItemType.product.value and not self.psid.data:
        #     raise ValidationError(message='商品标签必需对应场景')  # 不再需要对应场景
        if raw.data != ItemType.product.value and self.psid.data:
            raise ValidationError(message='非商品标签无需对应场景')
        self.ittype = raw

    def validate_itauthority(self, raw):
        if raw.data:
            try:
                ItemAuthrity(raw.data)
            except Exception as e:
                raise ParamsError('itauthority权限设置不合法')

