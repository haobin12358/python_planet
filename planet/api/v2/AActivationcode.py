from planet.common.base_resource import Resource
from planet.control.CActivationCode import CActivationCode


class AActivationCode(Resource):
    def __init__(self):
        self.cact_code = CActivationCode()

    def get(self, act_code):
        apis = {
            'list_act_code': self.cact_code.get_user_activationcode,
            'get_rule': self.cact_code.get_rule,
            'get_list': self.cact_code.get_list,
            'get_actcode_list': self.cact_code.get_actcode_list,
            'get_actcode_detail':self.cact_code.get_actcode_detail

        }
        return apis

    def post(self, act_code):
        apis = {
            'apply': self.cact_code.create_apply,
            'rule': self.cact_code.set_rule,
        }
        return apis
