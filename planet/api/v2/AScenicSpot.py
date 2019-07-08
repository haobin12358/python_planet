# -*- coding: utf-8 -*-
from planet.common.base_resource import Resource
from planet.control.CScenicSpot import CScenicSpot


class AScenicSpot(Resource):
    """景区"""
    def __init__(self):
        self.cscenicspot = CScenicSpot()

    def get(self, scenicspot):
        apis = {
            'get': self.cscenicspot.get,                                # 景区详情
            'list': self.cscenicspot.list,                              # 景区列表
            'travelrecord_list': self.cscenicspot.travelrecord_list,    # 时光记录列表
            'get_travelrecord': self.cscenicspot.get_travelrecord       # 时光记录详情
        }
        return apis

    def post(self, scenicspot):
        apis = {
            'add': self.cscenicspot.add,                                # 添加景区
            'update': self.cscenicspot.update,                          # 编辑景区
            'delete': self.cscenicspot.delete,                          # 删除景区
            'add_travelrecord': self.cscenicspot.add_travelrecord,      # 发布时光记录
        }
        return apis
