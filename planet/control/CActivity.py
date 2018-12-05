# 活动总控制
import json
from datetime import date

from flask import request

from planet.common.success_response import Success
from planet.common.token_handler import is_tourist
from planet.config.enums import OrderMainStatus, ActivityType, ApplyStatus
from planet.extensions.register_ext import db
from planet.extensions.validates.activty import ActivityUpdateForm, ActivityGetForm, ParamsError
from planet.models import Activity, OrderMain, GuessNumAwardApply, MagicBoxApply, ProductSku, Products, MagicBoxJoin
from .CUser import CUser


class CActivity(CUser):
    def list(self):
        """获取正在进行中的活动"""
        # 判断是否是新人, 没有已付款的订单则为新人
        if not is_tourist():
            usid = request.user.id
            exists_order = OrderMain.query.filter_(
                OrderMain.USid == usid, OrderMain.OMstatus > OrderMainStatus.wait_pay.value
            ).first()
        else:
            exists_order = False
        if exists_order:
            activitys = Activity.query.filter_by_().filter_(
                Activity.ACtype != ActivityType.fresh_man.value,
                Activity.ACshow == True
            ).order_by(Activity.ACsort).all()
        else:
            activitys = Activity.query.filter_by_().order_by(Activity.ACsort).all()
        result = []
        for act in activitys:
            act.fields = ['ACbackGround', 'ACbutton', 'ACtype', 'ACname']
            act.fill('ACtype_zh', ActivityType(act.ACtype).zh_value)
            # 活动是否有供应上参与
            today = date.today()
            if ActivityType(act.ACtype).name == 'guess_num':
                lasting = GuessNumAwardApply.query.filter_by_().filter(
                    GuessNumAwardApply.GNAAstatus == ApplyStatus.agree.value,
                    GuessNumAwardApply.AgreeStartime <= today,
                    GuessNumAwardApply.AgreeEndtime >= today,
                ).first()
                if lasting:
                    result.append(act)
            elif ActivityType(act.ACtype).name == 'magic_box':
                lasting = MagicBoxApply.query.filter_by_().filter(
                    MagicBoxApply.MBAstatus == ApplyStatus.agree.value,
                    GuessNumAwardApply.AgreeStartime <= today,
                    GuessNumAwardApply.AgreeEndtime >= today,
                ).first()
                if lasting:
                    result.append(act)
            else:
                result.append(act)

        return Success(data=result)

    def update(self):
        """设置活动的基本信息"""
        form = ActivityUpdateForm().valid_data()
        with db.auto_commit():
            act = form.activity
            act.update({
                'ACbackGround': form.acbackground.data,
                'ACtopPic': form.actoppic.data,
                'ACbutton': form.acbutton.data,
                'ACshow': form.acshow.data,
                'ACdesc': form.acdesc.data,
                'ACname': form.acname.data,
                'ACsort': form.acsort.data,
            })
            db.session.add(act)
        return Success('修改成功')

    def get(self):
        form = ActivityGetForm().valid_data()
        act_instance = form.activity
        ac_type = ActivityType(form.actype.data).name
        mbaid = form.mbaid.data
        usid_base = form.usid_base.data
        if not usid_base:
            usid = None if is_tourist() else request.user.id
        else:
            usid = self._base_decode(usid_base)
        today = date.today()
        act_instance.hide('ACid', 'ACbackGround', 'ACbutton', 'ACtopPic')
        if ac_type == 'magic_box':  # 魔盒
            if not mbaid:
                product, magic_apply = db.session.query(Products, MagicBoxApply).join(
                    ProductSku, ProductSku.PRid == Products.PRid
                ).join(
                    MagicBoxApply, MagicBoxApply.SKUid == ProductSku.SKUid
                ).filter_(
                    MagicBoxApply.AgreeStartime <= today,
                    MagicBoxApply.AgreeEndtime >= today,
                    MagicBoxApply.isdelete == False,
                ).first_('活动未在进行')
            else:
                product, magic_apply = db.session.query(Products, MagicBoxApply).join(
                    ProductSku, ProductSku.PRid == Products.PRid
                ).join(
                    MagicBoxApply, MagicBoxApply.SKUid == ProductSku.SKUid
                ).filter_(
                    # MagicBoxApply.AgreeStartime <= today,
                    # MagicBoxApply.AgreeEndtime >= today,
                    MagicBoxApply.MBAid == mbaid,
                    MagicBoxApply.isdelete == False,
                ).first_('活动不存在')

            act_instance.fill('prpic', product.PRmainpic)
            magic_apply.fileds = [
                'SKUprice', 'SKUminPrice', 'Gearsone',
                'Gearstwo', 'Gearsthree', 'AgreeStartime',
                'AgreeEndtime', 'MBAid', 'SKUprice', 'SKUminPrice'
            ]
            magic_apply.Gearsone = json.loads(magic_apply.Gearsone or '[]')
            magic_apply.Gearstwo = json.loads(magic_apply.Gearstwo or '[]')
            magic_apply.Gearsthree = json.loads(magic_apply.Gearsthree or '[]')
            act_instance.fill('infos', magic_apply)
            # 当前价格
            if usid is not None:
                magic_box_join = MagicBoxJoin.query.filter_by_({
                    'MBAid': mbaid,
                    'USid': usid
                }).first()
                if magic_box_join:
                    magic_apply.fill('current_price', magic_box_join.MBJcurrentPrice)
        elif ac_type == 'guess_num':
            apply = Products.query.join(
                ProductSku, Products.PRid == ProductSku.PRid
            ).join(
                GuessNumAwardApply, GuessNumAwardApply.SKUid == ProductSku.SKUid
            ).filter_(
                GuessNumAwardApply.AgreeStartime <= today,
                GuessNumAwardApply.AgreeEndtime >= today,
                MagicBoxApply.isdelete == False,
            ).first_('活动未在进行')
            act_instance.ACdesc = act_instance.ACdesc.split('|')
            act_instance.fill('prpic', apply.PRmainpic)
        return Success(data=act_instance)


