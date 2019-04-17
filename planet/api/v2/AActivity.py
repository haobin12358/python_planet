from planet.common.base_resource import Resource
from planet.control.CActivity import CActivity


class AActivity(Resource):
    def __init__(self):
        self.cactivity = CActivity()

    def get(self, activity):
        apis = {
            'list': self.cactivity.list,
            'get': self.cactivity.get,
        }
        return apis

    def post(self, activity):
        apis = {
            'update': self.cactivity.update,
        }
        return apis
