from planet.common.base_resource import Resource
from planet.control.CMessage import CMessage


class AMessage(Resource):
    def __init__(self):
        self.cmessage = CMessage()

    def get(self, message):
        apis = {
            'test': self.cmessage.test,
            'get': self.cmessage.get_platform_message
        }
        return apis

    def post(self, message):
        apis = {
            'set': self.cmessage.set_message
        }
        return apis
