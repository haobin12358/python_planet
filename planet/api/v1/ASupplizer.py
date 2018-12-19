from planet.common.base_resource import Resource
from planet.control.CSupplizer import CSupplizer


class ASupplizer(Resource):
    def __init__(self):
        self.csupplizer = CSupplizer()

    def get(self, supplizer):
        apis = {
            'list': self.csupplizer.list,
            'get': self.csupplizer.get,
            'code': self.csupplizer.send_reset_password_code,
        }
        return apis

    def post(self, supplizer):
        apis = {
            'create': self.csupplizer.create,
            'update': self.csupplizer.update,
            'reset_password': self.csupplizer.reset_password,
            'change_password': self.csupplizer.change_password,
            'offshelves': self.csupplizer.offshelves,
        }
        return apis
