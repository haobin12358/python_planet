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
            'login_test': self.user.login_test,
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
            'check_idcode': self.user.check_idcode,
            'get_profile': self.user.get_profile,
            'get_safecenter': self.user.get_safecenter,
            'get_identifyinginfo': self.user.get_identifyinginfo,
        }
        return apis

