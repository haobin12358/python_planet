from planet.common.base_resource import Resource
from planet.control.CTimeLimited import CTimeLimited


class ATimelimited(Resource):
    def __init__(self):
        self.ctl = CTimeLimited()

    def get(self, timelimited):
        apis = {
            'get': self.ctl.get,
            'list_activity': self.ctl.list_activity,
            'list_product': self.ctl.list_product,
            'list_activity_product': self.ctl.list_activity_product,
            # 'get': self.ctl.get,
        }
        return apis

    def post(self, timelimited):
        apis = {
            'create': self.ctl.create,
            'apply_award': self.ctl.apply_award,
            'update_activity': self.ctl.update_activity,
            'shelf_award': self.ctl.shelf_award,
            'del_award': self.ctl.del_award,
            'reapply_award':  self.ctl.reapply_award,
            'update_award': self.ctl.update_award
        }
        return apis
