from planet.common.base_resource import Resource
from planet.control.CMessage import CMessage


class AMessage(Resource):
    def __init__(self):
        self.cmessage = CMessage()

    def get(self, message):
        apis = {
            'test': self.cmessage.test,
            'get': self.cmessage.get_platform_message,
            'read': self.cmessage.read,
            'get_room_list': self.cmessage.get_room_list,
            'get_message_list': self.cmessage.get_message_list,
        }
        return apis

    def post(self, message):
        apis = {
            'set': self.cmessage.set_message,
            'del_room': self.cmessage.del_room,
            'read_message': self.cmessage.read_message,
            'create_room': self.cmessage.create_room
        }
        return apis
