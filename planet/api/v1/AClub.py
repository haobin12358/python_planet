# -*- coding: utf-8 -*-
from planet.control.CClub import CClub
from planet.common.base_resource import Resource

class AClub(Resource):

    def __init__(self):
        self.cclub = CClub()

    def post(self, club):
        apis = {
            'create': self.cclub.create_userwords,
            "create_message": self.cclub.create_companymessage
        }
        return apis

    def get(self, club):
        apis = {
            "list": self.cclub.companymessage_list,
            "message": self.cclub.companymessage_message
        }
        return apis