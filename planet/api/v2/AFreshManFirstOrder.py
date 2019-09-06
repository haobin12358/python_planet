from planet.common.base_resource import Resource
from planet.control.CFreshManFirstOrder import CFreshManFirstOrder


class AFreshManFirstOrder(Resource):
    def __init__(self):
        self.creshman = CFreshManFirstOrder()

    def get(self, fresh_man):
        apis = {
            'list': self.creshman.list,
            'get': self.creshman.get,
            'award_detail': self.creshman.award_detail,
            'list_apply': self.creshman.list_apply,
        }
        return apis

    def post(self, fresh_man):
        apis = {
            'add_order': self.creshman.add_order,
            'apply_award': self.creshman.apply_award,
            'update_award': self.creshman.update_award,
            'shelf_award': self.creshman.shelf_award,
            'delete': self.creshman.del_award,
        }
        return apis

