# 小程序 用来创建活动 管理活动
from planet.common.base_resource import Resource
from planet.control.CPlay import CPlay


class APlay(Resource):
    def __init__(self):
        cplay = CPlay()

    def get(self, play):
        apis = {}
        return apis

    def post(self, play):
        apis = {}
        return apis
