# -*- coding: utf-8 -*-
from planet.common.base_resource import Resource
from planet.control.CGuessGroup import CGuessGroup


class AGuessGroup(Resource):
    def __init__(self):
        self.cguessgroup = CGuessGroup()

    def get(self, guessgroup):
        apis = {
            'get': self.cguessgroup.get,                # 拼团商品详情
            'list': self.cguessgroup.list,              # 拼团/商品列表
        }
        return apis

    def post(self, guessgroup):
        apis = {
            'apply': self.cguessgroup.apply,            # 申请商品
            'update': self.cguessgroup.update,          # 编辑商品
            'cancel': self.cguessgroup.cancel_apply,    # 取消申请
            'delete': self.cguessgroup.delete,          # 删除申请
            'shelf': self.cguessgroup.shelf,            # 下架商品
            'join': self.cguessgroup.join,              # 参加拼团
            'order': self.cguessgroup.order             # 创建订单

        }
        return apis

