from .base_form import *


class CommsionUpdateForm(BaseForm):
    levelcommision = FieldList(DecimalField('佣金比'))
    invitenum = IntegerField('邀请人数', default=0)
    groupsale = DecimalField('团队佣金')
    pesonalsale = DecimalField('个人销售额')
    invitenumscale = DecimalField('下次升级/上次升级邀请人数比')
    groupsalescale = DecimalField('下次升级/上次升级 团队销售额比')
    pesonalsalescale = DecimalField('下次升级/上次升级 个人销售额比')
    reduceratio = FieldList(DecimalField())
    increaseratio = FieldList(DecimalField())

    def validate_levelcommision(self, raw):
        if raw.data and len(raw.data) != 4:
            raise ParamsError('请设置四级佣金比')
        for comm in raw.data:
            if comm < 0 or comm > 100:
                raise ParamsError('佣金比不合适')

    def validate_reduceratio(self, raw):
        if raw.data and len(raw.data) != 4:
            raise ParamsError('请设置四级减额系数')

    def validate_increaseratio(self, raw):
        if raw.data and len(raw.data) != 4:
            raise ParamsError('请设置四级增额系数')
