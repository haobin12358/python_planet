from planet.common.base_resource import Resource
from planet.control.CMagicBox import CMagicBox


class AMagicBox(Resource):
    def __init__(self):
        self.cmagicbox = CMagicBox()

    def get(self, magicbox):
        apis = {
            'list': self.cmagicbox.list,    # 魔盒/商品列表
            'get': self.cmagicbox.get,      # 魔盒/商品详情

        }
        return apis

    def post(self, magicbox):
        apis = {
            'open': self.cmagicbox.open,                        # 拆盒
            'join': self.cmagicbox.join,                        # 参加
            'recv_award': self.cmagicbox.recv_award,            # 购买
            'apply_award': self.cmagicbox.apply_award,          # 申请
            'update_apply': self.cmagicbox.update_apply,        # 编辑
            'shelf_award': self.cmagicbox.shelf_award,          # 撤销
            'delete': self.cmagicbox.delete_apply,              # 删除
            'shelves': self.cmagicbox.shelves,                  # 下架
        }
        return apis
