# -*- coding: utf-8 -*-
from planet.control.CClub import CClub
from planet.common.base_resource import Resource

class AClub(Resource):

    def __init__(self):
        self.cclub = CClub()

    def post(self, club):
        apis = {
            'create': self.cclub.create_userwords
        }
        return apis