from planet.common.base_resource import Resource
from planet.control.CApproval import CApproval


class Aapproval(Resource):
    def __init__(self):
        self.approval = CApproval()

    def post(self, approval):
        apis = {
            'add_permission': self.approval.add_permission,
            'deal_approval': self.approval.deal_approval
        }
        return apis

    def get(self, approval):
        apis = {
        }
        return apis

