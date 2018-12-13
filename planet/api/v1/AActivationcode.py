from planet.common.base_resource import Resource
from planet.control.CActivationCode import CActivationCode


class AActivationCode(Resource):
    def __init__(self):
        self.cact_code = CActivationCode()

    def get(self, act_code):
        apis = {
            'list_act_code': self.cact_code.get_user_activationcode
        }
        return apis
