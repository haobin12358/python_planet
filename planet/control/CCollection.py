# -*- coding: utf-8 -*-
import uuid
from planet.extensions.register_ext import db
from planet.common.params_validates import parameter_required
from planet.models import UserCollection
from planet.common.success_response import Success


class CCollection:
    def collect(self):
        data = parameter_required(('collector', 'collection', 'cotype'))
        crusid = data.get('collector')
        ctid = data.get('collection')
        c = data.get('cotype')
        flag = UserCollection.query.filter(UserCollection.Collector == crusid,
                                           UserCollection.Collection == ctid, UserCollection.isdelete == False).first()
        if flag == None:
            uin = UserCollection.create({
                'UCid': str(uuid.uuid1()), 'Collector': crusid, 'Collection': ctid, 'CoType': c})
            db.session.add(uin)
            db.session.commit()
            return Success('添加成功')

    def cancel(self):
        data = parameter_required(('collector', 'cancelled'))
        crusid = data.get('collector')
        cancelid = data.get('cancelled')
        cancelid = cancelid.split()
        flag = UserCollection.query.filter(UserCollection.Collector == crusid,
                                           UserCollection.Collection == cancelid,
                                           UserCollection.isdelete == False).all()
        if flag != None:
            for i in flag:
                i.isdelete = False
            db.session.commit()
            return Success('修改成功')
        else:
            return Success('还未收藏这些商品')
