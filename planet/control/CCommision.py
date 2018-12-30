from planet.common.success_response import Success
from planet.common.token_handler import admin_required
from planet.config.enums import UserIdentityStatus
from planet.extensions.register_ext import db
from planet.extensions.validates.commision import CommsionUpdateForm
from planet.models import User, Commision


class CCommision:

    @admin_required
    def update(self):
        """平台分销佣金设置"""
        form = CommsionUpdateForm().valid_data()
        with db.auto_commit():
            commision = Commision.query.filter(
                Commision.isdelete == False
            ).first()
            if not commision:
                commision = Commision()
            commission_dict = {
                'Levelcommision': form.levelcommision.data,
                'InviteNum': form.invitenum.data,
                'GroupSale': form.groupsale.data,
                'PesonalSale': form.pesonalsale.data,
                'InviteNumScale': form.invitenumscale.data,
                'GroupSaleScale': form.groupsalescale.data,
                'PesonalSaleScale': form.pesonalsalescale.data,
                'ReduceRatio': form.reduceratio.data,
                'IncreaseRatio': form.increaseratio.data,
            }
            [setattr(commision, k, v) for k, v in commission_dict.items() if v]
            db.session.add(commision)
        return Success('修改成功')

    def get(self):
        commision = Commision.query.filter(
            Commision.isdelete == False,
        ).first()
        return Success(data=commision)

