from planet.common.base_resource import Resource
from planet.control.CFreshManFirstOrder import CFreshManFirstOrder


class AFreshManFirstOrder(Resource):
    def __init__(self):
        self.creshman = CFreshManFirstOrder()

    def get(self, fresh_man):
        apis = {
            'list': self.creshman.list,
            'get': self.creshman.get,
        }
        return apis

    def post(self, fresh_man):
        apis = {
            'add_order': self.creshman.add_order,
        }
        return apis

