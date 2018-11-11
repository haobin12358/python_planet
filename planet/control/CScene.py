# -*- coding: utf-8 -*-
import uuid

from planet.common.success_response import Success
from planet.extensions.validates.product import SceneCreateForm
from planet.models import ProductScene
from planet.service.SProduct import SProducts


class CScene(object):
    def __init__(self):
        self.sproducts = SProducts()

    def list(self):
        """列出所有场景"""
        scenes = self.sproducts.get_product_scenes()
        return Success(data=scenes)

    def create(self):
        """创建场景"""
        form = SceneCreateForm().valid_data()
        with self.sproducts.auto_commit() as s:
            product_scene_instance = ProductScene.create({
                'PSid': str(uuid.uuid4()),
                'PSpic': form.pspic.data,
                'PSname': form.psname.data,
                'PSsort': form.pssort.data,
            })
            s.add(product_scene_instance)
        return Success('创建成功')
