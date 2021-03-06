from planet.common.base_resource import Resource
from planet.control.CMaterialFeedback import CMaterialFeedback


class AMaterialFeedback(Resource):
    def __init__(self):
        self.cmf = CMaterialFeedback()

    def get(self, feedback):
        apis = {
            'get': self.cmf.get,
            'list': self.cmf.list,
            'details': self.cmf.get_details,
            'get_ticket_linkage': self.cmf.get_ticket_linkage,
        }
        return apis

    def post(self, feedback):
        apis = {
            'create': self.cmf.create,
            'refuse': self.cmf.refuse,
            'refund': self.cmf.refund
        }
        return apis
