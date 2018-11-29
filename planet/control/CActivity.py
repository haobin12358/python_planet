# 活动总控制
from flask import request

from planet.common.success_response import Success
from planet.common.token_handler import is_tourist
from planet.config.enums import OrderMainStatus, ActivityType
from planet.extensions.register_ext import db
from planet.extensions.validates.activty import ActivityUpdateForm
from planet.models import Activity, OrderMain


class CActivity:
    def list(self):
        """获取正在进行中的活动"""
        # 判断是否是新人, 没有已付款的订单则为新人
        if not is_tourist():
            usid = request.user.id
            exists_order = OrderMain.query.filter_(
                OrderMain.USid == usid, OrderMain.OMstatus > OrderMainStatus.wait_pay.value
            )
        else:
            exists_order = False
        if exists_order:
            activitys = Activity.query.filter_by_().filter_(
                Activity.ACtype != ActivityType.fresh_man.value,
                Activity.ACshow == True
            ).order_by(Activity.ACsort).all()
        else:
            activitys = Activity.query.filter_by_().order_by(Activity.ACsort).all()
        for act in activitys:
            act.fields = ['ACbackGround', 'ACbutton', 'ACtype', 'ACname']
            act.fill('ACtype_zh', ActivityType(act.ACtype).zh_value)

        return Success(data=activitys)

    def update(self):
        """设置活动的基本信息"""
        form = ActivityUpdateForm().valid_data()
        acid = form.acid.data
        with db.auto_commit():
            act = Activity.query.filter_by_({'ACid': acid}).first_('活动不存在')

