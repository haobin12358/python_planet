from planet.common.base_resource import Resource
from planet.control.CSupplizer import CSupplizer


class ASupplizer(Resource):
    def __init__(self):
        self.csupplizer = CSupplizer()

    def get(self, supplizer):
        apis = {
            'list': self.csupplizer.list,
            'get': self.csupplizer.get,
        }
        return apis

    def post(self, supplizer):
        apis = {
            'create': self.csupplizer.create,
            'update': self.csupplizer.update,
        }
        return apis
