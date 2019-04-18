# -*- coding: utf-8 -*-
import uuid

from planet.config.enums import CollectionType
from planet.extensions.register_ext import db
from planet.common.params_validates import parameter_required
from planet.models import UserCollectionLog
from planet.common.success_response import Success
from planet.common.token_handler import token_required, usid_to_token, get_current_user
from flask import request, current_app


class CCollection:

    @token_required
    def collect(self):
        data = parameter_required(('uclcollection', 'uclcotype'))
        user = get_current_user()
        # crusid = user
        ctid = data.get('uclcollection')
        c = data.get('uclcotype', 0)
        try:
            c = CollectionType(c).value
        except:
            current_app.logger.info('get colletcion type {} error '.format(c))
            c = 0
        flag = UserCollectionLog.query.filter(
            UserCollectionLog.UCLcollector == user.USid, UserCollectionLog.UCLcoType == c,
            UserCollectionLog.UCLcollection == ctid, UserCollectionLog.isdelete == False).first()

        with db.auto_commit():
            if flag:
                flag.isdelete = True
                return Success('取消收藏成功')

            uin = UserCollectionLog.create({
                'UCLid': str(uuid.uuid1()), 'UCLcollector': user.USid, 'UCLcollection': ctid, 'UCLcoType': c})
            db.session.add(uin)

            return Success('添加收藏成功')

    @token_required
    def show(self):

        # data = parameter_required('collector')  # token 获取当前操作用户

        # collector = data.get('collector')
        flag = UserCollectionLog.query.filter(UserCollectionLog.UCLcollector == request.user.id,
                                              UserCollectionLog.isdelete == False).all()
        # 增加筛选条件 收藏类型
        for i in flag:
            i.fill('')



