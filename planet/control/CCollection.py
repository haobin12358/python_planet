# -*- coding: utf-8 -*-
import uuid

from planet.config.enums import CollectionType
from planet.extensions.register_ext import db
from planet.common.params_validates import parameter_required
from planet.models import UserCollectionLog, News
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
        # 该接口废弃
        return
        # data = parameter_required('collector')  # token 获取当前操作用户

        # collector = data.get('collector')
    #     data = parameter_required(('uclcoType', 0))
    #     user = get_current_user()
    #     try:
    #         cotype = CollectionType(data.get('uclcoType')).value
    #     except:
    #         current_app.logger.info('获取 cotype 失败 {}'.format(data.get('uclcoType')))
    #         cotype = 0
    #
    #     ucl_list = UserCollectionLog.query.filter(
    #         UserCollectionLog.UCLcollector == user.USid, UserCollectionLog.UCLcoType == cotype,
    #         UserCollectionLog.isdelete == False).all()
    #
    # def _fill_news(self, ucl_list):
    #     for ucl in ucl_list:
    #         news = News.query.filter_by(NEid=ucl.UCLcollection, isdelete=False).first()
    #


