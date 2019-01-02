import json

from planet.common.success_response import Success
from planet.common.token_handler import admin_required
from planet.config.enums import UserIdentityStatus
from planet.extensions.register_ext import db
from planet.extensions.validates.commision import CommsionUpdateForm, ParamsError
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
            from planet import JSONEncoder
            commission_dict = {
                'Levelcommision': json.dumps(form.levelcommision.data, cls=JSONEncoder),
                'InviteNum': form.invitenum.data,
                'GroupSale': form.groupsale.data,
                'PesonalSale': form.pesonalsale.data,
                'InviteNumScale': form.invitenumscale.data,
                'GroupSaleScale': form.groupsalescale.data,
                'PesonalSaleScale': form.pesonalsalescale.data,
                'ReduceRatio': json.dumps(form.reduceratio.data, cls=JSONEncoder),
                'IncreaseRatio': json.dumps(form.increaseratio.data, cls=JSONEncoder),
            }
            [setattr(commision, k, v) for k, v in commission_dict.items() if v is not None and v != '[]']
            if not commision.InviteNum and not commision.PesonalSale and not commision.GroupSale:
                raise ParamsError('升级条件不可全为0')
            if sum(commision.Levelcommision) >= 100:
                raise ParamsError('总佣金比大于100')
            db.session.add(commision)
        return Success('修改成功')

    def get(self):
        commision = Commision.query.filter(
            Commision.isdelete == False,
        ).first()
        commision.Levelcommision = json.loads(commision.Levelcommision)
        commision.ReduceRatio = json.loads(commision.ReduceRatio)
        commision.IncreaseRatio = json.loads(commision.IncreaseRatio)
        return Success(data=commision)

