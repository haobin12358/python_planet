import random
import uuid

from dateutil.utils import today
from sqlalchemy.dialects.postgresql import json

from planet.common.error_response import StatusError
from planet.common.success_response import Success
from planet.common.token_handler import token_required
from planet.config.enums import ApplyStatus
from planet.extensions.register_ext import db
from planet.extensions.validates.activty import MagicBoxOpenForm, ParamsError, MagicBoxCreateForm, request
from planet.models import MagicBoxJoin, MagicBoxApply, GuessNumAwardApply, MagicBoxOpen


class CMagicBox:
    def __init__(self):
        pass

    def open(self):
        """好友帮拆"""
        form = MagicBoxOpenForm().valid_data()
        usid_base = form.usid_base.data  # 用以标志来源用户
        level = form.level.data
        mbaid = form.mbaid.data  # 用以标志拆盒活动
        # 活动是否在进行
        magic_box_apply = MagicBoxApply.query.filter_by_().filter(
            MagicBoxApply.MBAid == mbaid,
            MagicBoxApply.MBAstatus == ApplyStatus.agree.value
        ).first_('活动不存在')
        lasting = magic_box_apply >= today
        if not lasting:
            raise StatusError('活动过期')
        try:
            usid = self._base_decode(usid_base)
        except ValueError:
            raise ParamsError()
        # 来源用户参与状况
        magic_box_join = MagicBoxJoin.query.filter_by().filter(
            MagicBoxJoin.USid == usid,
            MagicBoxJoin.MBAid == mbaid
        ).order_by(MagicBoxJoin.createtime.desc()).first()

        with db.auto_commit():
            # 来源用户未参加
            if not magic_box_join:
                mbjid = str(uuid.uuid1())   # 参与活动的id
                magboxjoin = MagicBoxJoin.create({
                    'MBJid': mbjid,
                    'USid': usid,
                    'MBAid': mbaid,
                    'MBJprice': magic_box_apply.SKUprice
                })
                db.session.add(magboxjoin)
            else:
                mbjid = magic_box_apply.MBAid
            # 开拆
            levle_attr = dict(form.level.choices).get(level)
            current_level_str = getattr(magic_box_apply, levle_attr)
            current_level_json = json.loads(current_level_str)  # 列表 ["1-2", "3-4"]
            if len(current_level_json):
                current_level_json[1] = list(map(lambda x: x * -1, current_level_json[1].split('-')))  # 第1个元素是-
            current_level_json[0] = current_level_json[1].split('-')  # 第0个元素是+
            random_choice_first = random.choice(current_level_json)  # 选择是- 还是+
            current_choice = random.choice(random_choice_first)
            import ipdb
            ipdb.set_trace()
            mb_open = MagicBoxOpen.create({
                'MBOid': str(uuid.uuid1()),
                'USid': request.user.id,
                'MBJid': mbjid,
                'MBOgear': level,
            })

    @token_required
    def create(self):
        """参与活动, 分享前或分享后调用, 分享之后需要记住  base64(usid)和mbaid"""
        form = MagicBoxCreateForm().valid_data()
        mbaid = form.mbaid.data
        with db.auto_commit():
            magic_box_apply = MagicBoxApply.query.filter_by_().filter(
                MagicBoxApply.AgreeStartime <= today,
                MagicBoxApply.AgreeEndtime >= today,
                MagicBoxApply.MBAid == mbaid,
            ).first_('活动结束')
            magic_box_join = MagicBoxJoin.create({
                'MBJid': str(uuid.uuid1()),
                'USid': request.user.id,
                'MBAid': mbaid,
                'MBJprice': magic_box_apply.SKUprice,
            })
            db.session.add(magic_box_join)
        return Success('参与成功')

    def _get_current_lasting_magic(self):
        """正在进行中的魔盒活动"""
        lasting = MagicBoxApply.query.filter_by_().filter(
            MagicBoxApply.MBAstatus == ApplyStatus.agree.value,
            GuessNumAwardApply.AgreeStartime <= today,
            GuessNumAwardApply.AgreeEndtime >= today,
        ).first()

    def _base_decode(self, raw):
        import base64
        return base64.b64decode(raw + '=' * (4 - len(raw) % 4)).decode()

    def _base_encode(self, raw):
        import base64
        raw = raw.encode()
        return base64.b64encode(raw).decode()
