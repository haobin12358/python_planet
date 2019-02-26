# -*- coding: utf-8 -*-
import uuid

from planet.common.success_response import Success
from planet.common.token_handler import admin_required
from planet.extensions.validates.product import SceneCreateForm, SceneUpdateForm, SceneListForm
from planet.extensions.register_ext import db
from planet.models import ProductScene, SceneItem
from planet.service.SProduct import SProducts


class CScene(object):
    def __init__(self):
        self.sproducts = SProducts()

    def list(self):
        """列出所有场景"""
        form = SceneListForm().valid_data()
        kw = form.kw.data
        scenes = self.sproducts.get_product_scenes(kw)
        return Success(data=scenes)

    @admin_required
    def create(self):
        """创建场景"""
        form = SceneCreateForm().valid_data()
        with self.sproducts.auto_commit() as s:
            scene_dict = {
                'PSid': str(uuid.uuid1()),
                'PSpic': form.pspic.data,
                'PSname': form.psname.data,
                'PSsort': form.pssort.data,
            }
            product_scene_instance = ProductScene.create(scene_dict)
            s.add(product_scene_instance)

            # 每个场景下默认增加一个“大行星精选”标签
            default_scene_item = SceneItem.create({
                'SIid': str(uuid.uuid1()),
                'PSid': scene_dict.get('PSid'),
                'ITid': 'planet_featured'
            })
            s.add(default_scene_item)

        return Success('创建成功', data={
            'psid': product_scene_instance.PSid
        })

    @admin_required
    def update(self):
        form = SceneUpdateForm().valid_data()
        psid, pspic, psname, pssort = form.psid.data, form.pspic.data, form.psname.data, form.pssort.data
        isdelete = form.isdelete.data
        with db.auto_commit():
            pssort = self._check_sort(pssort)
            product_scene = ProductScene.query.filter(ProductScene.isdelete == False,
                                                      ProductScene.PSid == psid
                                                      ).first_('不存在的场景')
            product_scene.update({
                "PSpic": pspic,
                "PSname": psname,
                "PSsort": pssort,
                "isdelete": isdelete
            })
            db.session.add(product_scene)
            if isdelete is True:
                SceneItem.query.filter_by(PSid=psid).delete_()
        return Success('更新成功', {'psid': psid})

    def _check_sort(self, pssort):
        if not pssort:
            return 1
        pssort = int(pssort)
        if pssort < 1:
            return 1
        count_ps = ProductScene.query.filter_by_().count()
        if pssort > count_ps:
            return count_ps
        return pssort
