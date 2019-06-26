# 小程序 用来创建活动 管理活动
from planet.common.base_resource import Resource
from planet.control.CPlay import CPlay


class APlay(Resource):
    def __init__(self):
        self.cplay = CPlay()

    def get(self, play):
        apis = {

        }
        return apis

    def post(self, play):
        apis = {
            'set_play': self.cplay.set_play,
            'set_cost': self.cplay.set_cost,
            'set_insurance': self.cplay.set_insurance,
        }
        return apis
