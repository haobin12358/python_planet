# 活动总控制
import json
from datetime import date

from flask import request

from planet.common.success_response import Success
from planet.common.token_handler import is_tourist, is_admin, admin_required, is_supplizer
from planet.config.enums import OrderMainStatus, ActivityType, ApplyStatus, TrialCommodityStatus, AdminActionS
from planet.control.BaseControl import BASEADMIN
from planet.extensions.register_ext import db
from planet.extensions.validates.activty import ActivityUpdateForm, ActivityGetForm, ParamsError
from planet.models import Activity, OrderMain, GuessNumAwardApply, MagicBoxApply, ProductSku, Products, MagicBoxJoin, \
    MagicBoxOpen, TrialCommodity, FreshManFirstProduct, FreshManFirstApply, OutStock, GuessNumAwardProduct, \
    GroupGoodsProduct
from .CUser import CUser


class CActivity(CUser):
    def list(self):
        """获取正在进行中的活动"""
        # 判断是否是新人, 没有已付款的订单则为新人
        if is_tourist():
            exists_order = False
            filter_kwargs = dict(ACshow=True)
        elif is_admin():
            exists_order = False
            filter_kwargs = dict()
        else:
            usid = request.user.id
            exists_order = OrderMain.query.filter_(OrderMain.USid == usid,
                                                   OrderMain.OMstatus > OrderMainStatus.wait_pay.value
                                                   ).first()
            filter_kwargs = dict(ACshow=True)
        # if exists_order:
        #     activitys = Activity.query.filter_(Activity.ACtype != ActivityType.fresh_man.value,
        #                                        Activity.ACshow == True,
        #                                        Activity.isdelete == False
        #                                        ).order_by(Activity.ACsort).all()
        # else:
        activitys = Activity.query.filter_by_(filter_kwargs).order_by(Activity.ACsort).all()
        result = []
        today = date.today()
        for act in activitys:
            act.fields = ['ACbackGround', 'ACbutton', 'ACtype', 'ACname', 'ACshow', 'ACsort', 'ACdesc', 'ACtopPic']
            act.fill('actype_zh', ActivityType(act.ACtype).zh_value)
            # 活动是否有供应商参与
            if ActivityType(act.ACtype).name == 'guess_num':

                guess_num_count = GuessNumAwardProduct.query.filter(
                    GuessNumAwardProduct.GNAAid == GuessNumAwardApply.GNAAid,
                    GuessNumAwardApply.GNAAstatus == ApplyStatus.agree.value,
                    GuessNumAwardApply.isdelete == False,
                    GuessNumAwardProduct.isdelete == False,
                    GuessNumAwardApply.GNAAstarttime <= today,
                    GuessNumAwardApply.GNAAendtime >= today
                ).count()
                act.fill('prcount', guess_num_count)
            elif ActivityType(act.ACtype).name == 'magic_box':
                magic_box_count = MagicBoxApply.query.join(OutStock, OutStock.OSid == MagicBoxApply.OSid).filter(
                    OutStock.isdelete == False,
                    MagicBoxApply.isdelete == False,
                    MagicBoxApply.MBAstatus == ApplyStatus.agree.value,
                    MagicBoxApply.AgreeStartime <= today,
                    MagicBoxApply.AgreeEndtime >= today,
                ).count()
                act.fill('prcount', magic_box_count)
                stock = OutStock.query.join(MagicBoxApply, MagicBoxApply.OSid == OutStock.OSid).filter(
                    OutStock.isdelete == False,
                    MagicBoxApply.isdelete == False,
                    MagicBoxApply.MBAstatus == ApplyStatus.agree.value,
                    MagicBoxApply.AgreeStartime <= today,
                    MagicBoxApply.AgreeEndtime >= today
                ).first()
                act.fill('stock', getattr(stock, 'OSnum', ''))
            elif ActivityType(act.ACtype).name == 'free_use':
                free_use_count = TrialCommodity.query.filter(
                    TrialCommodity.TCstatus == TrialCommodityStatus.upper.value,
                    TrialCommodity.AgreeStartTime <= today,
                    TrialCommodity.AgreeEndTime >= today,
                    TrialCommodity.TCstocks > 0
                ).count()
                act.fill('prcount', free_use_count)
            elif ActivityType(act.ACtype).name == 'fresh_man':
                fresh_man_count = FreshManFirstProduct.query.join(
                    FreshManFirstApply, FreshManFirstProduct.FMFAid == FreshManFirstApply.FMFAid
                ).filter_(
                    FreshManFirstProduct.isdelete == False,
                    FreshManFirstApply.AgreeStartime <= today,
                    FreshManFirstApply.AgreeEndtime >= today,
                    FreshManFirstApply.FMFAstatus == ApplyStatus.agree.value,
                ).count()
                act.fill('prcount', fresh_man_count)
            elif ActivityType(act.ACtype).name == 'guess_group':
                gg_count = GroupGoodsProduct.query.filter(GroupGoodsProduct.isdelete == False,
                                                          GroupGoodsProduct.GPstatus == ApplyStatus.agree.value,
                                                          GroupGoodsProduct.GPday == today
                                                          ).count()
                act.fill('prcount', gg_count)
            else:
                act.fill('prcount', 0)
            if is_admin():
                result = activitys
            else:
                if ActivityType(act.ACtype).name == 'guess_num':
                    lasting = GuessNumAwardApply.query.filter(
                        GuessNumAwardApply.isdelete == False,
                        GuessNumAwardApply.GNAAstatus == ApplyStatus.agree.value,
                        GuessNumAwardApply.AgreeStartime <= today,
                        GuessNumAwardApply.AgreeEndtime >= today,
                        ).all()
                    if lasting:
                        result.append(act)
                elif ActivityType(act.ACtype).name == 'magic_box':
                    lasting = MagicBoxApply.query.join(OutStock, OutStock.OSid == MagicBoxApply.OSid).filter(
                        OutStock.isdelete == False,
                        OutStock.OSnum > 0,
                        MagicBoxApply.isdelete == False,
                        MagicBoxApply.MBAstatus == ApplyStatus.agree.value,
                        MagicBoxApply.AgreeStartime <= today,
                        MagicBoxApply.AgreeEndtime >= today,
                    ).first()
                    if lasting:
                        result.append(act)
                elif ActivityType(act.ACtype).name == 'free_use':
                    lasting = TrialCommodity.query.filter(TrialCommodity.TCstatus == TrialCommodityStatus.upper.value,
                                                          TrialCommodity.AgreeStartTime <= today,
                                                          TrialCommodity.AgreeEndTime >= today,
                                                          TrialCommodity.TCstocks > 0,
                                                          TrialCommodity.isdelete == False
                                                          ).first()
                    if lasting:
                        result.append(act)
                else:
                    result.append(act)
        return Success(data=result)

    @admin_required
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
            BASEADMIN().create_action(AdminActionS.update.value, 'Activity', str(act.ACid))
        return Success('修改成功')

    def get(self):
        form = ActivityGetForm().valid_data()
        act_instance = form.activity
        ac_type = ActivityType(form.actype.data).name
        mbjid = form.mbjid.data
        mbaid = None
        if not mbjid:
            usid = None if is_tourist() else request.user.id
        else:
            magic_box_join = MagicBoxJoin.query.filter_by({'MBJid': mbjid}).first()
            if magic_box_join:
                usid = magic_box_join.USid
                mbaid = magic_box_join.MBAid
            else:
                usid = None if is_tourist() else request.user.id

        today = date.today()
        act_instance.hide('ACid', 'ACbackGround', 'ACbutton', 'ACtopPic')
        if ac_type == 'magic_box':  # 魔盒
            if not mbjid:
                query = db.session.query(Products, MagicBoxApply).join(
                    ProductSku, ProductSku.PRid == Products.PRid
                ).join(
                    MagicBoxApply, MagicBoxApply.SKUid == ProductSku.SKUid
                ).filter_(
                    MagicBoxApply.AgreeStartime <= today,
                    MagicBoxApply.AgreeEndtime >= today,
                    MagicBoxApply.isdelete == False,
                )
                if not is_admin() and not is_supplizer():
                    query = query.filter(
                        MagicBoxApply.MBAstatus == ApplyStatus.agree.value,
                   )
                product, magic_apply = query.first_('活动未在进行中')
                mbaid = magic_apply.MBAid
            else:
                magic_box_join = MagicBoxJoin.query.filter(
                    MagicBoxJoin.isdelete == False,
                    MagicBoxJoin.MBJid == mbjid,
                ).first_('活动不存在')
                product, magic_apply = db.session.query(Products, MagicBoxApply).join(
                    ProductSku, ProductSku.PRid == Products.PRid
                ).join(
                    MagicBoxApply, MagicBoxApply.SKUid == ProductSku.SKUid
                ).filter_(
                    # MagicBoxApply.AgreeStartime <= today,
                    # MagicBoxApply.AgreeEndtime >= today,
                    MagicBoxApply.MBAid == magic_box_join.MBAid,
                    MagicBoxApply.isdelete == False
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
                    # 判断是否是自己的盒子:
                    if not is_tourist() and request.user.id == magic_box_join.USid:
                        can_buy = True
                    else:
                        can_buy = False
                    magic_apply.fill('can_buy', can_buy)
                    # 拆盒记录
                    mbp_history = MagicBoxOpen.query.filter_by_({'MBJid': magic_box_join.MBJid}).order_by(MagicBoxOpen.createtime.desc()).limit(4).all()
                    magic_apply.fill('open_history', mbp_history)

        # todo 是否需要判断前后台
        elif ac_type == 'guess_num':
            # apply = Products.query.join(
            #     ProductSku, Products.PRid == ProductSku.PRid
            # ).join(
            #     GuessNumAwardApply, GuessNumAwardApply.SKUid == ProductSku.SKUid
            # ).filter_(
            #     GuessNumAwardApply.AgreeStartime <= today,
            #     GuessNumAwardApply.AgreeEndtime >= today,
            #     MagicBoxApply.isdelete == False,
            # ).first_('活动未在进行')
            # apply = GuessNumAwardApply.query.filter_by(
            #     GuessNumAwardApply.GNAAstarttime <= today,
            #     GuessNumAwardApply.GNAAendtime >= today).order_by(
            #     GuessNumAwardApply.createtime.desc()).first_('活动未进行')
            #
            # gnap = GuessNumAwardProduct.query.filter_by(GNAAid=apply.GNAAid, isdelete=False).first_('活动未进行')
            apply = GuessNumAwardProduct.query.filter(
                    GuessNumAwardProduct.GNAAid == GuessNumAwardApply.GNAAid,
                    GuessNumAwardApply.isdelete == False,
                    GuessNumAwardProduct.isdelete == False,
                    GuessNumAwardApply.GNAAstarttime <= today,
                    GuessNumAwardApply.GNAAendtime >= today
                ).order_by(GuessNumAwardApply.createtime.desc()).first_('活动未进行')
            act_instance.ACdesc = act_instance.ACdesc.split('|')
            act_instance.fill('prpic', apply.PRmainpic)
        return Success(data=act_instance)


