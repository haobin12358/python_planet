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
            'get_travelrecord': self.cscenicspot.get_travelrecord,      # 时光记录详情
            'raiders_list': self.cscenicspot.get_raiders_list,          # 景区下推荐攻略列表
            'get_team_travelrecord': self.cscenicspot.get_team,         # 团队广场下推荐攻略列表
            'get_toilet': self.cscenicspot.get_toilet,                  # 厕所详情
            'toilet_list': self.cscenicspot.toilet_list,                # 厕所列表
            'ac_callback': self.cscenicspot.ac_callback,                # 多服务器access_token共用回调
            'get_team_album': self.cscenicspot.get_team_album,          # 团队相册
        }
        return apis

    def post(self, scenicspot):
        apis = {
            'add': self.cscenicspot.add,                                # 添加景区
            'update': self.cscenicspot.update,                          # 编辑景区
            'delete': self.cscenicspot.delete,                          # 删除景区
            'add_travelrecord': self.cscenicspot.add_travelrecord,      # 发布时光记录
            'del_travelrecord': self.cscenicspot.del_travelrecord,      # 删除时光记录
            'add_toilet': self.cscenicspot.add_toilet,                  # 添加厕所
            'update_toilet': self.cscenicspot.update_toilet,            # 编辑厕所
            'share_content': self.cscenicspot.share_content,            # 团队广场分享前自定义内容
        }
        return apis
