# -*- coding: utf-8 -*-
import uuid

from planet.config.enums import ItemType
from planet.extensions.validates.Item import ItemCreateForm, ItemListForm
from planet.service.SProduct import SProducts
from planet.common.success_response import Success
from planet.common.token_handler import token_required
from planet.models import ProductScene, Items, SceneItem


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
        recommend = True if str(recommend) == '1' else None
        items = self.sproduct.get_items([
            Items.ITtype == ittype,
            Items.ITrecommend == recommend,
            SceneItem.PSid == psid
        ], (Items.ITsort, Items.ITid))
        for item in items:
            item.fill('ITtype_zh', ItemType(item.ITtype).zh_value)
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
            s_list = []
            if psid:
                s.query(ProductScene).filter_by_({'PSid': psid}).first_('不存在的场景')
            # 添加标签
            item_dict = {
                'ITid': str(uuid.uuid4()),
                'ITname': itname,
                'ITsort': itsort,
                'ITdesc': itdesc,
                'ITtype': ittype,
            }
            items_instance = Items.create(item_dict)
            s_list.append(items_instance)
            # 标签场景标签表
            if psid:
                scene_item_dict = {
                    'PSid': psid,
                    'ITid': item_dict.get('ITid'),
                    'SIid': str(uuid.uuid4())
                }
                scene_item_instance = SceneItem.create(scene_item_dict)
                s_list.append(scene_item_instance)
            s.add_all(s_list)
        return Success('添加成功')
