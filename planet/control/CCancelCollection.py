# -*- coding: utf-8 -*-
import uuid
from planet.extensions.register_ext import db
from planet.common.params_validates import parameter_required
from planet.models import UserCollection
from planet.common.success_response import Success


class CCancelCollection:
    def cancel (self):
        data = parameter_required (('collector', 'cancelled'))
        crusid = data.get('collector')
        cancelid = data.get('cancelled')
        cancelid = cancelid.split()
        a=len(cancelid)
        for i in range(a):
            flag = UserCollection.query.filter(UserCollection.Collector == crusid,
                                               UserCollection.Collection == cancelid[i],
                                               UserCollection.isdelete == 0).first()
            flag.isdelete = 1
        return Success('修改成功')
        #假设修改是建立在收藏一定存在的前提下