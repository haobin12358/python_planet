# -*- coding: utf-8 -*-
from planet.common.base_resource import Resource
from planet.control.CMiniProgramPersonalCenter import CMiniProgramPersonalCenter


class AMiniProgramPersonalCenter(Resource):
    def __init__(self):
        self.cmppc = CMiniProgramPersonalCenter()

    def post(self, personalcenter):
        apis = {
            'guide_certification': self.cmppc.guide_certification,
        }
        return apis

    def get(self, personalcenter):
        apis = {
            'my_wallet': self.cmppc.my_wallet,
            'guide': self.cmppc.guide
        }
        return apis
