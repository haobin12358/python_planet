from planet.common.base_resource import Resource
from planet.control.CSigninSetting import CSigninSetting


class ASigninSetting(Resource):
    def __init__(self):
        self.cign = CSigninSetting()

    def get(self, siginsetting):
        apis = {
            'get_all_signsetting': self.cign.get_all
        }
        return apis

    def post(self, siginsetting):
        apis = {
            'add_or_update_signsetting': self.cign.add_or_update,
            'delete_signsetting': self.cign.delete
        }
        return apis

