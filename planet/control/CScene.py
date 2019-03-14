# -*- coding: utf-8 -*-
from datetime import datetime, timedelta
import uuid

from flask import current_app

from planet.common.success_response import Success
from planet.common.token_handler import admin_required, common_user, is_tourist
from planet.extensions.validates.product import SceneCreateForm, SceneUpdateForm, SceneListForm
from planet.extensions.register_ext import db
from planet.models import ProductScene, SceneItem
from planet.service.SProduct import SProducts


class CScene(object):
    def __init__(self):
        self.sproducts = SProducts()

    def list(self):
        """列出所有场景"""
        now = datetime.now()
        form = SceneListForm().valid_data()
        kw = form.kw.data
        query = ProductScene.query.filter(ProductScene.isdelete == False)
        if kw:
            query = query.filter(ProductScene.PSname.contains(kw))
        scenes = query.order_by(ProductScene.PSsort, ProductScene.createtime).all()
        res = list()
        for scene in scenes:
            if scene.PStimelimited:
                if scene.PSstarttime < now < scene.PSendtime:
                    countdown = scene.PSendtime - now
                    hours = str(countdown.days * 24 + (countdown.seconds // 3600))
                    minutes = str((countdown.seconds % 3600) // 60)
                    seconds = str((countdown.seconds % 3600) % 60)

                    scene.fill('countdown', "{}:{}:{}".format('0' + hours if len(hours) == 1 else hours,
                                                              '0' + minutes if len(minutes) == 1 else minutes,
                                                              '0' + seconds if len(seconds) == 1 else seconds))
                else:
                    if is_tourist() or common_user():
                        continue
            res.append(scene)
        return Success(data=res)

    @admin_required
    def create(self):
        """创建场景"""
        form = SceneCreateForm().valid_data()
        psendtime = form.psendtime.data
        with self.sproducts.auto_commit() as s:
            scene_dict = {
                'PSid': str(uuid.uuid1()),
                'PSpic': form.pspic.data,
                'PSname': form.psname.data,
                'PSsort': form.pssort.data,
                'PStimelimited': form.pstimelimited.data,
                'PSstarttime': form.psstarttime.data,
                'PSendtime': psendtime
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
        if form.pstimelimited.data:
            from planet.extensions.tasks import cancel_scene_association
            current_app.logger.info('限时场景结束时间 : {} '.format(psendtime))
            cancel_scene_association.apply_async(args=(scene_dict['PSid'],), eta=psendtime - timedelta(hours=8), )

        return Success('创建成功', data={
            'psid': product_scene_instance.PSid
        })

    @admin_required
    def update(self):
        form = SceneUpdateForm().valid_data()
        psid, pspic, psname, pssort = form.psid.data, form.pspic.data, form.psname.data, form.pssort.data
        pstimelimited, psstarttime, psendtime = form.pstimelimited.data, form.psstarttime.data, form.psendtime.data
        isdelete = form.isdelete.data
        with db.auto_commit():
            pssort = self._check_sort(pssort)
            product_scene = ProductScene.query.filter(ProductScene.isdelete == False,
                                                      ProductScene.PSid == psid
                                                      ).first_('不存在的场景')
            if isdelete:
                SceneItem.query.filter_by(PSid=psid).delete_()
                product_scene.isdelete = True
            else:
                product_scene.update({
                    "PSpic": pspic,
                    "PSname": psname,
                    "PSsort": pssort,
                    "PStimelimited": pstimelimited,
                    "PSstarttime": psstarttime,
                    "PSendtime": psendtime,
                }, null='not')
                db.session.add(product_scene)

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
