# 小程序 用来创建活动 管理活动
from planet.common.base_resource import Resource
from planet.control.CPlay import CPlay


class APlay(Resource):
    def __init__(self):
        self.cplay = CPlay()

    def get(self, play):
        apis = {
            'get_cost': self.cplay.get_cost,
            'get_all_play': self.cplay.get_all_play,
            'get_insurance': self.cplay.get_insurance,
            'get_play': self.cplay.get_play,
            'get_play_list': self.cplay.get_play_list,
        }
        return apis

    def post(self, play):
        apis = {
            'set_play': self.cplay.set_play,
            'set_cost': self.cplay.set_cost,
            'set_insurance': self.cplay.set_insurance,
        }
        return apis
