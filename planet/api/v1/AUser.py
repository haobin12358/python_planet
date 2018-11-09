# -*- coding: utf-8 -*-
from planet.common.base_resource import Resource
from planet.control.CUser import CUser


class AUser(Resource):
    def __init__(self):
        self.user = CUser()

    def post(self, user):
        apis = {
            'login': self.user.login,
            'login_test': self.user.login_test,
            # 'update': self.user.update,
            # 'destroy': self.user.destroy,
        }
        return apis

    def get(self, user):
        apis = {
            'get_inforcode': self.user.get_inforcode,
            'get_home': self.user.get_home,
        }
        return apis

