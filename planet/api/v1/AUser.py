# -*- coding: utf-8 -*-
from planet.common.base_resource import Resource
from planet.control.CUser import CUser


class AUser(Resource):
    def __init__(self):
        self.user = CUser()

    def post(self, user):
        apis = {
            'login': self.user.login,
            'add_address': self.user.add_useraddress,
            'update_address': self.user.update_useraddress,
            # 'update': self.user.update,
            # 'destroy': self.user.destroy,
        }
        return apis

    def get(self, user):
        apis = {
            'get_inforcode': self.user.get_inforcode,
            'get_home': self.user.get_home,
            'get_all_address': self.user.get_useraddress,
            'get_one_address': self.user.get_one_address,
        }
        return apis

