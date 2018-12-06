import random
import uuid
from datetime import date
from decimal import Decimal

from sqlalchemy.dialects.postgresql import json

from planet.common.error_response import StatusError, DumpliError
from planet.common.success_response import Success
from planet.common.token_handler import token_required
from planet.config.enums import ApplyStatus, ActivityType, ActivityRecvStatus
from planet.extensions.register_ext import db
from planet.extensions.validates.activty import MagicBoxOpenForm, ParamsError, MagicBoxCreateForm, request
from planet.models import MagicBoxJoin, MagicBoxApply, GuessNumAwardApply, MagicBoxOpen, User, Activity
from .CUser import CUser


class CMagicBox(CUser):
    def __init__(self):
        pass

    @token_required
    def open(self):
        """好友帮拆"""
        # 判断帮拆活动总控制是否结束
        Activity.query.filter_by({
            'ACtype': ActivityType.magic_box.value
        }).first_('活动已结束')

        form = MagicBoxOpenForm().valid_data()
        mbjid = form.mbjid.data
        level = form.level.data
        levle_attr = dict(form.level.choices).get(level)
        usid = request.user.id
        # 源参与记录
        magic_box_join = MagicBoxJoin.query.filter_by({'MBJid': mbjid}).first_('来源参数异常(mbjid)')
        if magic_box_join.MBJstatus != ActivityRecvStatus.wait_recv.value:
            raise StatusError('已领奖或已过期')
        mbaid = magic_box_join.MBAid
        # 活动是否在进行
        magic_box_apply = MagicBoxApply.query.filter_by_().filter(
            MagicBoxApply.MBAid == mbaid,
            MagicBoxApply.MBAstatus == ApplyStatus.agree.value
        ).first_('活动不存在')
        today = date.today()
        lasting = magic_box_apply.AgreeEndtime >= today
        if not lasting:
            raise StatusError('活动过期')
        with db.auto_commit():
            # 是否已经帮开奖
            ready_open = MagicBoxOpen.query.filter_by_({'USid': usid,
                                                        'MBJid': mbjid}).first()
            if ready_open:
                raise DumpliError('已经帮好友拆过')
            # 价格变动随机
            current_level_str = getattr(magic_box_apply, levle_attr)
            current_level_json = json.loads(current_level_str)  # 列表 ["1-2", "3-4"]

            current_level_json[0] = list(map(lambda x: int(x) * -1, current_level_json[0].split('-')))  # 第0个元素是-
            if len(current_level_json) == 2:
                current_level_json[1] = list(map(int, current_level_json[1].split('-')))  # 第1个元素是+
            random_choice_first = random.choice(current_level_json)  # 选择是- 还是+
            final_reduce = random.uniform(*random_choice_first)  # 最终价格变动
            final_reduce = round(Decimal(final_reduce), 2)
            # 价格计算
            final_price = Decimal(magic_box_join.MBJcurrentPrice) + final_reduce
            if final_price > magic_box_apply.SKUprice:
                final_price = magic_box_apply.SKUprice
            if final_price < magic_box_apply.SKUminPrice:
                final_price = magic_box_apply.SKUminPrice
            final_price = round(final_price, 2)
            # 帮拆记录
            user = User.query.filter_by_({'USid': usid}).first()
            mb_open = MagicBoxOpen.create({
                'MBOid': str(uuid.uuid1()),
                'USid': usid,
                'MBJid': mbjid,
                'MBOgear': int(level),
                'MBOresult': float(final_reduce),
                'MBOprice': float(final_price),
                'USname': user.USname
            })
            # 源参与价格修改
            magic_box_join.MBJcurrentPrice = float(final_price)
            db.session.add(mb_open)
        return Success(data={
            'final_reduce': float(final_reduce),
            'final_price': float(final_price)
        })

    @token_required
    def join(self):
        """参与活动, 分享前(或分享后调用), 创建用户的参与记录
        """
        # 判断帮拆活动总控制是否结束
        Activity.query.filter_by({
            'ACtype': ActivityType.magic_box.value
        }).first_('活动已结束')
        form = MagicBoxCreateForm().valid_data()
        mbaid = form.mbaid.data
        usid = request.user.id
        with db.auto_commit():
            today = date.today()
            magic_box_apply = MagicBoxApply.query.filter_by_().filter(
                MagicBoxApply.AgreeStartime <= today,
                MagicBoxApply.AgreeEndtime >= today,
                MagicBoxApply.MBAid == mbaid
            ).first_('活动结束')
            Activity.query.filter_by_({

            })
            # 已参与则不再新建记录
            magic_box_join = MagicBoxJoin.query.filter_by_({
                'USid': usid,
                'MBAid': mbaid
            }).first()
            if not magic_box_join:
                # 一期活动只可参与一次
                magic_box_join = MagicBoxJoin.create({
                    'MBJid': str(uuid.uuid1()),
                    'USid': usid,
                    'MBAid': mbaid,
                    'MBJprice': magic_box_apply.SKUprice,
                })
                db.session.add(magic_box_join)
            else:
                # 但是可以多次分享
                if magic_box_join.MBJstatus == ActivityRecvStatus.ready_recv.value:
                    raise StatusError('本期已参与')
        return Success('参与成功', data={
            'mbjid': magic_box_join.MBJid
        })
