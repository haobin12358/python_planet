import random
import uuid
from datetime import date
from decimal import Decimal

from sqlalchemy.dialects.postgresql import json

from planet.common.error_response import StatusError, DumpliError
from planet.common.success_response import Success
from planet.common.token_handler import token_required
from planet.config.enums import ApplyStatus
from planet.extensions.register_ext import db
from planet.extensions.validates.activty import MagicBoxOpenForm, ParamsError, MagicBoxCreateForm, request
from planet.models import MagicBoxJoin, MagicBoxApply, GuessNumAwardApply, MagicBoxOpen


class CMagicBox:
    def __init__(self):
        pass

    @token_required
    def open(self):
        """好友帮拆"""
        form = MagicBoxOpenForm().valid_data()
        usid_base = form.usid_base.data  # 用以标志来源用户
        level = form.level.data
        levle_attr = dict(form.level.choices).get(level)
        mbaid = form.mbaid.data  # 用以标志拆盒活动
        # 活动是否在进行
        magic_box_apply = MagicBoxApply.query.filter_by_().filter(
            MagicBoxApply.MBAid == mbaid,
            MagicBoxApply.MBAstatus == ApplyStatus.agree.value
        ).first_('活动不存在')
        today = date.today()
        lasting = magic_box_apply.AgreeEndtime >= today
        if not lasting:
            raise StatusError('活动过期')
        try:
            usid = self._base_decode(usid_base)
        except ValueError:
            raise ParamsError('usid_base异常')

        with db.auto_commit():
            # 来源用户参与状况
            magic_box_join = MagicBoxJoin.query.filter_by().filter(
                MagicBoxJoin.USid == usid,
                MagicBoxJoin.MBAid == mbaid
            ).order_by(MagicBoxJoin.createtime.desc()).first()
            # 来源用户未参加
            if not magic_box_join:
                mbjid = str(uuid.uuid1())   # 参与活动的id
                magic_box_join = MagicBoxJoin.create({
                    'MBJid': mbjid,
                    'USid': usid,
                    'MBAid': mbaid,
                    'MBJprice': magic_box_apply.SKUprice
                })
                db.session.add(magic_box_join)
                db.session.flush()
            else:  # 来源用户已参加
                mbjid = magic_box_join.MBJid
                ready_open = MagicBoxOpen.query.filter_by_({'USid': request.user.id,
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
            mb_open = MagicBoxOpen.create({
                'MBOid': str(uuid.uuid1()),
                'USid': request.user.id,
                'MBJid': mbjid,
                'MBOgear': int(level),
                'MBOresult': float(final_reduce),
                'MBOprice': float(final_price),
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
        """参与活动, 分享前(或分享后调用), 用来代表用户参与了此活动
        """
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
            # 已参与则不再新建记录
            already_join = MagicBoxJoin.query.filter_by_({
                'USid': usid,
                'MBAid': mbaid
            }).first()
            if not already_join:
                magic_box_join = MagicBoxJoin.create({
                    'MBJid': str(uuid.uuid1()),
                    'USid': usid,
                    'MBAid': mbaid,
                    'MBJprice': magic_box_apply.SKUprice,
                })
                db.session.add(magic_box_join)
        return Success('参与成功', data={
            'usid_base': self._base_encode(usid),
            'mbaid': mbaid,
        })

    def _base_decode(self, raw):
        import base64
        return base64.b64decode(raw + '=' * (4 - len(raw) % 4)).decode()

    def _base_encode(self, raw):
        import base64
        raw = raw.encode()
        return base64.b64encode(raw).decode()
