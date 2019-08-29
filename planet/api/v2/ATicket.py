from planet.common.base_resource import Resource
from planet.control.CTicket import CTicket


class ATicket(Resource):
    def __init__(self):
        self.cticket = CTicket()

    def get(self, ticket):
        apis = {
            'get': self.cticket.get_ticket,
            'list': self.cticket.list_ticket,
            'list_linkage': self.cticket.list_linkage,
        }
        return apis

    def post(self, ticket):
        apis = {
            'create': self.cticket.create_ticket,
            'update': self.cticket.update_ticket,
            'pay': self.cticket.pay,
        }
        return apis
