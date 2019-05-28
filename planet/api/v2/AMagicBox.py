from planet.common.base_resource import Resource
from planet.control.CMagicBox import CMagicBox


class AMagicBox(Resource):
    def __init__(self):
        self.cmagicbox = CMagicBox()

    def get(self, magicbox):
        apis = {
            'list': self.cmagicbox.list,

        }
        return apis

    def post(self, magicbox):
        apis = {
            'open': self.cmagicbox.open,
            'join': self.cmagicbox.join,
            'recv_award': self.cmagicbox.recv_award,
            'apply_award': self.cmagicbox.apply_award,
            'reapply_award': self.cmagicbox.reapply_award,
            'update_apply': self.cmagicbox.update_apply,
            'shelf_award': self.cmagicbox.shelf_award,
            'award_detail': self.cmagicbox.award_detail,
            'delete': self.cmagicbox.delete_apply,
            'shelves': self.cmagicbox.shelves,
        }
        return apis
