# -*- coding: utf-8 -*-
import uuid
from planet.extensions.register_ext import db
from planet.common.params_validates import parameter_required
from planet.models import UserCollection
from planet.common.success_response import Success


class CCollection:
    def collect (self):
        global ctid
        data = parameter_required (('collector', 'collection','cotype'))
        crusid=data.get('collector')
        ctid=data.get('collection')
        c=data.get('cotype')
        flag= UserCollection.query.filter(UserCollection.Collector == crusid,
                                          UserCollection.Collection == ctid,
                                          UserCollection.isdelete ==0).first()
        if flag ==None:
            uin = UserCollection.create({
                    'UCid':str(uuid.uuid1()),'Collector' : crusid,'Collection' :ctid,'CoType':c })
            db.session.add(uin)
            db.session.commit()
            return Success('添加成功')