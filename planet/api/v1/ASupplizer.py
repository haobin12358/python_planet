from planet.common.base_resource import Resource
from planet.control.CSupplizer import CSupplizer


class ASupplizer(Resource):
    def __init__(self):
        self.csupplizer = CSupplizer()

    def get(self, supplizer):
        apis = {
            'list': self.csupplizer.list,
        }
        return apis