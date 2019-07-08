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
            'get_playrequire': self.cplay.get_playrequire,
            'get_enterlog': self.cplay.get_enterlog,
            'get_gather': self.cplay.get_gather,
            'identity': self.cplay.identity,
            'get_signin': self.cplay.get_signin,
            'get_enter_user': self.cplay.get_enter_user,
            'get_notice': self.cplay.get_notice,
            'get_current_location': self.cplay.get_current_location,
            'get_member_location': self.cplay.get_member_location,
            'get_current_play': self.cplay.get_current_play,
        }
        return apis

    def post(self, play):
        apis = {
            'set_play': self.cplay.set_play,
            'set_cost': self.cplay.set_cost,
            'set_insurance': self.cplay.set_insurance,
            'join': self.cplay.join,
            'wechat_notify': self.cplay.wechat_notify,
            'set_signin': self.cplay.set_signin,
            'signin': self.cplay.signin,
            'set_gather': self.cplay.set_gather,
            'create_notice': self.cplay.create_notice,
            'help': self.cplay.help
        }
        return apis
