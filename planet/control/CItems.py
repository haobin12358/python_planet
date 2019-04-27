# -*- coding: utf-8 -*-
import json
import re
import uuid

from flask import request

from planet.common.error_response import StatusError, DumpliError
from planet.config.enums import ItemType, ItemAuthrity, ItemPostion, ProductStatus, CollectionType
from planet.extensions.register_ext import db
from planet.extensions.validates.Item import ItemCreateForm, ItemListForm, ItemUpdateForm
from planet.service.SProduct import SProducts
from planet.common.success_response import Success
from planet.common.token_handler import token_required, is_supplizer, admin_required, is_admin, common_user
from planet.models import ProductScene, Items, SceneItem, Products, ProductItems, UserCollectionLog


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

            scene_items = [sit.ITid for sit in
                           SceneItem.query.filter(SceneItem.PSid == psid, SceneItem.isdelete == False,
                                                  ProductScene.isdelete == False).all()]
            prscene_count = Products.query.outerjoin(ProductItems, ProductItems.PRid == Products.PRid
                                                     ).filter(Products.isdelete == False,
                                                              Products.PRfeatured == True,
                                                              Products.PRstatus == ProductStatus.usual.value,
                                                              ProductItems.isdelete == False,
                                                              ProductItems.ITid.in_(list(set(scene_items)))
                                                              ).count()
            if not prscene_count:
                items_query = items_query.filter(Items.ITid != 'planet_featured')  # 如果该场景下没有精选商品，不显示“大行星精选”标签

        if is_supplizer():
            # 供应商下不显示被限时场景关联着的标签
            time_limit_itids = [it.ITid for it in
                                Items.query.join(SceneItem, SceneItem.ITid == Items.ITid
                                                 ).join(ProductScene, ProductScene.PSid == SceneItem.PSid
                                                        ).filter(SceneItem.isdelete == False,
                                                                 ProductScene.isdelete == False,
                                                                 Items.isdelete == False,
                                                                 ProductScene.PStimelimited == True).all()]
            items_query = items_query.filter(Items.ITauthority == ItemAuthrity.no_limit.value,
                                             Items.ITposition.in_([ItemPostion.scene.value,
                                                                   ItemPostion.news_bind.value]
                                                                  ),
                                             Items.ITid.notin_(time_limit_itids),
                                             Items.ITid != 'planet_featured'
                                             )
        if is_admin():
            items_query = items_query.filter(Items.ITid != 'planet_featured')

        if kw:
            items_query = items_query.filter(
                Items.ITname.contains(kw)
            )
        items_query = items_query.order_by(Items.ITsort.asc(), Items.createtime.desc())

        # 普通用户默认获取已经自选过的圈子标签
        if str(ittype) == str(ItemType.news.value) and common_user():
            items = self._filter_new_items(request.user.id, option=form.option.data)
            return Success(data=items)
        items = items_query.all()
        for item in items:
            item.fill('ITtype_zh', ItemType(item.ITtype).zh_value)
            if item.ITtype == ItemType.product.value:
                pr_scene = ProductScene.query.outerjoin(SceneItem, SceneItem.PSid == ProductScene.PSid
                                                        ).filter_(SceneItem.isdelete == False,
                                                                  SceneItem.ITid == item.ITid,
                                                                  ProductScene.isdelete == False).all()
                if (is_supplizer() or is_admin()) and pr_scene:
                    psname_list = str([ps.PSname for ps in pr_scene])
                    psname_list = re.sub(r'[\[\]\'\,]+', '', psname_list)
                    item.ITname = getattr(item, 'ITname', '') + ' / ' + str(psname_list)  # 后台要显示标签所属场景

                item.fill('prscene', pr_scene)
        return Success('获取成功', data=items)

    def _filter_new_items(self, uid, option=None):
        """筛选出用户自选的圈子标签"""
        ucs = UserCollectionLog.query.filter_by_(UCLcollector=uid,
                                                 UCLcoType=CollectionType.news_tag.value).first()
        item_query = Items.query.filter(Items.isdelete == False,
                                        Items.ITtype == ItemType.news.value).order_by(Items.ITsort.asc(),
                                                                                      Items.createtime.desc()
                                                                                      )
        if option:
            if ucs:
                itids = json.loads(ucs.UCLcollection)
                my_item = item_query.filter(Items.ITid.in_(itids)).all()
                candidate_item = item_query.filter(Items.ITid.notin_(itids)).all()
            else:
                my_item = []
                candidate_item = item_query.all()
            items = dict(my_item=my_item, candidate_item=candidate_item)
        else:
            if ucs:
                itids = json.loads(ucs.UCLcollection)
                items = item_query.filter(Items.ITid.in_(itids)).all()
            else:
                items = item_query.all()
        return items

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
            if s.query(Items).filter_by(ITname=itname, ITtype=ittype, isdelete=False).first():
                raise DumpliError("您输入的标签名已存在")
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
        itname = form.itname  # 这里不要在后面加data
        isdelete = form.isdelete.data
        if itid in ['planet_featured', 'index_hot', 'news_bind_product', 'news_bind_coupon', 'index_brand',
                    'index_brand_product', 'index_recommend_product_for_you', 'upgrade_product'] and isdelete is True:
            raise StatusError('系统默认标签不能被删除')

        Items.query.filter_by_(ITid=itid).first_("未找到该标签")
        if not isdelete and Items.query.filter(Items.ITid != itid, Items.ITname == itname,
                                               Items.ITtype == form.ittype.data, Items.isdelete == False).first():
            raise DumpliError("您输入的标签名已存在")
        with db.auto_commit():
            itsort = self._check_itsort(form.itsort.data, form.ittype.data)
            item_dict = {'ITname': itname,
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
