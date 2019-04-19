# -*- coding: utf-8 -*-
import uuid

from planet.common.error_response import ParamsError
from planet.config.enums import CollectionType, UserGrade
from planet.extensions.register_ext import db
from planet.common.params_validates import parameter_required
from planet.models import UserCollectionLog, News, User, Admin, Supplizer, Products
from planet.common.success_response import Success
from planet.common.token_handler import token_required, get_current_user
from flask import current_app


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

        ctid = self._check_type_id(c, ctid)
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
        """获取当前关注的人 或者 自己的粉丝"""
        data = parameter_required(('showtype', ))
        user = get_current_user()
        showtype = data.get('showtype', 'follow')
        if showtype == 'follow':
            ucl_list = UserCollectionLog.query.filter_by(
                UCLcollector=user.USid, isdelete=False, UCLcoType=CollectionType.user.value).order_by(
                UserCollectionLog.createtime.desc()).all_with_page()
            # ucl_return_list = []
            for ucl in ucl_list:
                # 监测自己关注的是否也关注了自己
                # mutual_concern =
                ucl.fill('mutual_concern', bool(UserCollectionLog.query.filter_by(
                    UCLcollector=ucl.UCLcollection, isdelete=False,
                    UCLcollection=user.USid, UCLcoType=CollectionType.user.value).first()))

                ucl.fill('fens_count', UserCollectionLog.query.filter_by(
                    UCLcollection=ucl.UCLcollection, isdelete=False, UCLcoType=CollectionType.user.value).count())
                self._fill_user_info(ucl, ucl.UCLcollection)

        else:
            ucl_list = UserCollectionLog.query.filter_by(
                    UCLcollection=user.USid, isdelete=False, UCLcoType=CollectionType.user.value).all_with_page()
            for ucl in ucl_list:
                # 监测自己是否关注自己的粉丝
                ucl.fill('mutual_concern', bool(UserCollectionLog.query.filter_by(
                    UCLcollector=user.USid, isdelete=False,
                    UCLcollection=ucl.UCLcollector, UCLcoType=CollectionType.user.value).first()))

                ucl.fill('fens_count', UserCollectionLog.query.filter_by(
                    UCLcollection=ucl.UCLcollector, isdelete=False, UCLcoType=CollectionType.user.value).count())
                self._fill_user_info(ucl, ucl.UCLcollector)
        return Success(data=ucl_list)

    def _fill_user_info(self, ucl, usid):
        user = User.query.filter_by(USid=usid, isdelete=False).first()
        admin = Admin.query.filter_by(ADid=usid, isdelete=False).first()
        sup = Supplizer.query.filter_by(SUid=usid, isdelete=False).first()

        if user:
            ucl.fill('usname', user.USname)
            ucl.fill('usheader', user['USheader'])
            ucl.fill('uslevel', user.USlevel)
            ucl.fill('uslevel_en', UserGrade(user.USlevel).name)
            ucl.fill('uslevel_zn', UserGrade(user.USlevel).zh_value)
            return
        if admin:
            ucl.fill('usname', admin.ADname)
            ucl.fill('usheader', admin['ADheader'])
            ucl.fill('uslevel', 10)
            ucl.fill('uslevel_en', 'admin')
            ucl.fill('uslevel_zn', '管理员')
        if sup:
            ucl.fill('usname', sup.SUname)
            ucl.fill('usheader', sup['SUheader'])
            ucl.fill('uslevel', 5)
            ucl.fill('uslevel_en', 'supplizer')
            ucl.fill('uslevel_zn', '供应商')

    def _check_type_id(self, cotype, ctid):
        if cotype == CollectionType.product.value:
            product = Products.query.filter_by(PRid=ctid, isdelete=False).first_('关注失败, 商品已下架')
            ctid = product.PRid
        if cotype == CollectionType.news.value:
            news = News.query.filter_by(NEid=ctid, isdelete=False).first_('关注失败，圈子已被删除')
            ctid = news.NEid
        if cotype == CollectionType.user.value:
            news = News.query.filter_by(NEid=ctid, isdelete=False).first()
            user = User.query.filter_by(USid=ctid, isdelete=False).first()
            if not news and not user:
                current_app.logger.info('get cotype is {} ctid is {}'.format(cotype, ctid))
                raise ParamsError('关注失败，用户已删除')
            ctid = news.USid if news else user.USid
        return ctid