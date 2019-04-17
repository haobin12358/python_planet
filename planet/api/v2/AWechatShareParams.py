# -*- coding: utf-8 -*-
from planet.common.base_resource import Resource
from planet.control.CWechatShareParams import CWechatShareParams


class AWechatShareParams(Resource):
    def __init__(self):
        self.cwechatshareparams = CWechatShareParams()

    def get(self, shareparams):
        apis = {
            'get': self.cwechatshareparams.get_share_params,
        }
        return apis

    def post(self, shareparams):
        apis = {
            'set': self.cwechatshareparams.set_share_params,
        }
        return apis
