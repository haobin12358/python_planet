# -*- coding: utf-8 -*-
import uuid

from planet.common.error_response import StatusError
from planet.config.enums import ItemType, ItemAuthrity, ItemPostion
from planet.extensions.register_ext import db
from planet.extensions.validates.Item import ItemCreateForm, ItemListForm, ItemUpdateForm
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
        kw = form.kw.data
        recommend = form.recommend.data
        recommend = True if str(recommend) == '1' else None

        # 如果查询商品对应的标签, 则可以传场景的id
        items_query = Items.query.filter_(Items.isdelete == False, Items.ITtype == ittype,
                                          Items.ITrecommend == recommend, Items.ITauthority != ItemAuthrity.other.value,
                                          Items.ITposition != ItemPostion.other.value,
                                          )

        if psid:
            items_query = items_query.outerjoin(SceneItem, SceneItem.ITid == Items.ITid
                                                ).filter_(SceneItem.isdelete == False,
                                                          SceneItem.PSid == psid,
                                                          )
        if is_supplizer():
            items_query = items_query.filter(Items.ITauthority == ItemAuthrity.no_limit.value,
                                             Items.ITposition.in_([ItemPostion.scene.value,
                                                                   ItemPostion.news_bind.value]
                                                                  )
                                             )
        if kw:
            items_query = items_query.filter(
                Items.ITname.contains(kw)
            )
        items_query = items_query.order_by(Items.ITposition.desc(), Items.ITsort, Items.createtime, Items.ITid)
        items = items_query.all()
        for item in items:
            item.fill('ITtype_zh', ItemType(item.ITtype).zh_value)
            if item.ITtype == ItemType.product.value:
                pr_scene = ProductScene.query.outerjoin(SceneItem, SceneItem.PSid == ProductScene.PSid
                                                        ).filter_(SceneItem.ITid == item.ITid,
                                                                  ProductScene.isdelete == False).all()
                item.fill('prscene', pr_scene)
        return Success('获取成功', data=items)

    @admin_required
    def create(self):
        form = ItemCreateForm().valid_data()
        psid = form.psid.data
        itname = form.itname.data
        itsort = form.itsort.data
        itdesc = form.itdesc.data
        ittype = form.ittype.data
        itrecommend = form.itrecommend.data
        itid = str(uuid.uuid1())
        with self.sproduct.auto_commit() as s:
            s_list = []
            # 添加标签
            item_dict = {
                'ITid': itid,
                'ITname': itname,
                'ITsort': itsort,
                'ITdesc': itdesc,
                'ITtype': ittype,
                'ITrecommend': itrecommend
            }
            items_instance = Items.create(item_dict)
            s_list.append(items_instance)
            # 标签场景标签表
            if psid:
                for psi in psid:
                    s.query(ProductScene).filter_by_({'PSid': psi}).first_('不存在的场景')
                    scene_item_dict = {
                        'PSid': psi,
                        'ITid': itid,
                        'SIid': str(uuid.uuid1())
                    }
                    scene_item_instance = SceneItem.create(scene_item_dict)
                    s_list.append(scene_item_instance)
            s.add_all(s_list)
        return Success('添加成功', {'itid': itid})

    @admin_required
    def update(self):
        """修改标签"""
        form = ItemUpdateForm().valid_data()
        psid = form.psid.data
        itid = form.itid.data
        isdelete = form.isdelete.data
        if itid in ['index_hot', 'news_bind_product', 'news_bind_coupon', 'index_brand', 'index_brand_product',
                    'index_recommend_product_for_you', 'upgrade_product'] and isdelete is True:
            raise StatusError('系统默认标签不能被删除')

        Items.query.filter_by_(ITid=itid).first_("未找到该标签")
        with db.auto_commit():
            itsort = self._check_itsort(form.itsort.data, form.ittype.data)
            item_dict = {'ITname': form.itname.data,
                         'ITsort': itsort,
                         'ITdesc': form.itdesc.data,
                         'ITtype': form.ittype.data,
                         'ITrecommend': form.itrecommend.data,
                         'isdelete': isdelete
                         }
            # item_dict = {k: v for k, v in item_dict.items() if v is not None}
            Items.query.filter_by_(ITid=itid).update(item_dict)

            # 标签场景标签表
            if psid:
                old_psids = list()
                scene_items = SceneItem.query.filter_by_(ITid=itid).all()
                [old_psids.append(scene_item.PSid) for scene_item in scene_items]  # 获取已存在的关联psid
                for psi in psid:
                    ProductScene.query.filter_by_({'PSid': psi}).first_('不存在的场景')
                    if psi not in old_psids:
                        scene_item_dict = {
                            'PSid': psi,
                            'ITid': itid,
                            'SIid': str(uuid.uuid1())
                        }
                        scene_item_instance = SceneItem.create(scene_item_dict)
                        db.session.add(scene_item_instance)
                    else:
                        old_psids.remove(psi)
                [SceneItem.query.filter_by(PSid=droped_psid, ITid=itid).delete_() for droped_psid in old_psids]
            else:
                SceneItem.query.filter_by(ITid=itid).delete_()  # psid = [] 为空时，删除所有该标签场景的关联
        return Success('修改成功', {'itid': itid})

    def _check_itsort(self, itsort, ittype):

        if itsort < 1:
            return 1
        count_item = Items.query.filter_by_(ITtype=ittype).count()
        if itsort > count_item:
            return count_item
        return itsort
