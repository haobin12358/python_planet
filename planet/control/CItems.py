# -*- coding: utf-8 -*-
import uuid

from planet.extensions.validates.Item import ItemCreateForm, ItemListForm
from planet.service.SProduct import SProducts
from planet.common.success_response import Success
from planet.common.token_handler import token_required
from planet.models import ProductScene, Items


class CItems:
    def __init__(self):
        self.sproduct = SProducts()

    def list(self):
        """列出标签"""
        form = ItemListForm().valid_data()
        ittype = form.ittype.data
        psid = form.psid.data
        recommend = form.recommend.data
        # 如果查询商品对应的标签, 则可以传场景的id
        items = self.sproduct.get_items({'ITtype': ittype, 'PSid': psid, })
        return Success('获取成功', data=items)

    @token_required
    def create(self):
        form = ItemCreateForm().valid_data()
        psid = form.psid.data
        itname = form.itname.data
        itsort = form.itsort.data
        itdesc = form.itdesc.data
        ittype = form.ittype.data
        with self.sproduct.auto_commit() as s:
            if psid:
                s.query(ProductScene).filter_by_({'PSid': psid}).first_('不存在的场景')
            item_dict = {
                'ITid': str(uuid.uuid4()),
                'PSid': psid,
                'ITname': itname,
                'ITsort': itsort,
                'ITdesc': itdesc,
                'ITtype': ittype
            }
            items_instance = Items.create(item_dict)
            s.add(items_instance)
        return Success('添加成功')
