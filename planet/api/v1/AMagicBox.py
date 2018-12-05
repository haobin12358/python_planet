from planet.common.base_resource import Resource
from planet.control.CMagicBox import CMagicBox


class AMagicBox(Resource):
    def __init__(self):
        self.cmagicbox = CMagicBox()

    def post(self, magicbox):
        apis = {
            'open': self.cmagicbox.open,
            'join': self.cmagicbox.join,
        }
        return apis
