from planet.common.base_resource import Resource
from planet.control.CCommision import CCommision


class ACommission(Resource):
    def __init__(self):
        self.ccommision = CCommision()

    def post(self, comm):
        apis = {
            'update': self.ccommision.update,
        }
        return apis

    def get(self, comm):
        apis = {
            'get': self.ccommision.get,
        }
        return apis
