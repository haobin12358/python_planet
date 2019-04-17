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
            'get_supplizeraccount': self.csupplizer.get_supplizeraccount,
            'get_system_notes': self.csupplizer.get_system_notes,
        }
        return apis

    def post(self, supplizer):
        apis = {
            'create': self.csupplizer.create,
            'update': self.csupplizer.update,
            'delete': self.csupplizer.delete,
            'reset_password': self.csupplizer.reset_password,
            'change_password': self.csupplizer.change_password,
            'offshelves': self.csupplizer.offshelves,
            'set_supplizeraccount': self.csupplizer.set_supplizeraccount,
            'add_update_notes': self.csupplizer.add_update_notes,
        }
        return apis
