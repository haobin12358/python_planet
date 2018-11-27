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
            'upgrade_agent': self.user.upgrade_agent,
            'update_user': self.user.update_user,
            'user_sign_in': self.user.user_sign_in,
            'admin_login': self.user.admin_login,
            'add_admin_by_superadmin': self.user.add_admin_by_superadmin,
            'update_admin': self.user.update_admin,
            'wx_login': self.user.wx_login,
            'bing_telphone': self.user.bing_telphone,
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
            # 'check_idcode': self.user.check_idcode,
            # 'get_profile': self.user.get_profile,
            # 'get_safecenter': self.user.get_safecenter,
            'get_identifyinginfo': self.user.get_identifyinginfo,
            'get_upgrade': self.user.get_upgrade,
            'get_agent_center': self.user.get_agent_center,
            'get_agent_commission_list': self.user.get_agent_commission_list,
            'get_user_integral': self.user.get_user_integral,
            'get_admin_list': self.user.get_admin_list,
            'get_wxconfig': self.user.get_wxconfig,
        }
        return apis

