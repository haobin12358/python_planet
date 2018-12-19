# -*- coding: utf-8 -*-
import uuid

from planet.config.enums import ItemType, ItemAuthrity, ItemPostion
from planet.extensions.validates.Item import ItemCreateForm, ItemListForm
from planet.service.SProduct import SProducts
from planet.common.success_response import Success
from planet.common.token_handler import token_required, is_supplizer, admin_required
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
        items_query = Items.query.filter_(
            Items.isdelete == False,
            Items.ITtype == ittype,
            Items.ITrecommend == recommend,
            Items.ITauthority != ItemAuthrity.other.value,
            Items.ITposition != ItemPostion.other.value,
        ).order_by(
            Items.ITsort, Items.ITid
        )
        if ittype == ItemType.product.value or psid:
            items_query = items_query.outerjoin(
            SceneItem, SceneItem.ITid == Items.ITid
        ).filter_(
                SceneItem.isdelete == False,
                SceneItem.PSid == psid,
            )
        if is_supplizer():
            items_query = items_query.filter(
                Items.ITauthority == ItemAuthrity.no_limit.value,
                Items.ITposition.in_([ItemPostion.scene.value, ItemPostion.news_bind.value])
            )
        items = items_query.all()
        for item in items:
            item.fill('ITtype_zh', ItemType(item.ITtype).zh_value)
        return Success('获取成功', data=items)

    @admin_required
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
                for psi in psid:
                    scene_item_dict = {
                        'PSid': psi,
                        'ITid': item_dict.get('ITid'),
                        'SIid': str(uuid.uuid4())
                    }
                    scene_item_instance = SceneItem.create(scene_item_dict)
                    s_list.append(scene_item_instance)
            s.add_all(s_list)
        return Success('添加成功')

    @admin_required
    def update(self):
        # todo
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
                for psi in psid:
                    scene_item_dict = {
                        'PSid': psi,
                        'ITid': item_dict.get('ITid'),
                        'SIid': str(uuid.uuid4())
                    }
                    scene_item_instance = SceneItem.create(scene_item_dict)
                    s_list.append(scene_item_instance)
            s.add_all(s_list)
        return Success('添加成功')
