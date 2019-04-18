# -*- coding: utf-8 -*-
import uuid
from planet.extensions.register_ext import db
from planet.common.params_validates import parameter_required
from planet.models import UserCollection
from planet.common.success_response import Success
from planet.common.token_handler import token_required, usid_to_token
from flask import request


class CCollection:
    def collect(self):
        data = parameter_required(('collector', 'collection', 'cotype'))
        crusid = data.get('collector')
        ctid = data.get('collection')
        c = data.get('cotype')
        flag = UserCollection.query.filter(UserCollection.UCollector == crusid,
                                           UserCollection.UCollection == ctid, UserCollection.isdelete == False).first()

        with db.auto_commit():
            if flag == None:
                uin = UserCollection.create({
                    'UCid': str(uuid.uuid1()), 'Collector': crusid, 'Collection': ctid, 'CoType': c})
                db.session.add(uin)

                return Success('添加收藏成功')
            else:
                flag.isdelete = False
                return Success('取消收藏成功')

    @token_required
    def show(self):

        # data = parameter_required('collector')  # token 获取当前操作用户

        # collector = data.get('collector')
        flag = UserCollection.query.filter(UserCollection.UCollector == request.user.id,
                                           UserCollection.isdelete == False).all()
        # 增加筛选条件 收藏类型
        for i in flag:
            i.fill('')



