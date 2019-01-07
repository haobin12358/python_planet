# -*- coding: utf-8 -*-
import uuid

from planet.common.error_response import ParamsError, StatusError
from planet.common.params_validates import parameter_required
from planet.common.success_response import Success
from planet.common.token_handler import token_required, admin_required
from planet.config.enums import ProductStatus
from planet.extensions.register_ext import db
from planet.models import ProductCategory, Products
from .CProducts import CProducts


class CCategory(CProducts):

    def get_category(self):
        """获取类目"""
        data = parameter_required()
        up = data.get('up') or None
        deep = data.get('deep', 0)  # 深度
        pctype = 1 if not up else None
        categorys = self.sproduct.get_categorys({'ParentPCid': up, 'PCtype': pctype})
        for category in categorys:
            self._sub_category(category, deep)
        return Success(data=categorys)

    @admin_required
    def create(self):
        """创建分类"""
        data = parameter_required(('pcdesc', 'pcname', 'pcpic'))
        pcdesc = data.get('pcdesc')
        pcname = data.get('pcname')
        pcpic = data.get('pcpic')
        parentpcid = data.get('parentpcid')
        pcsort = data.get('pcsort', 1)
        assert isinstance(pcsort, int), 'pcsort 类型错误'
        # 检测是几级目录
        if not parentpcid:
            pctype = 1
        else:
            parent_catory = self.sproduct.get_category_one({'PCid': parentpcid}, '指定父级目录不存在')
            pctype = parent_catory.PCtype + 1
        with self.sproduct.auto_commit() as s:

            category_instance = ProductCategory.create({
                'PCid': str(uuid.uuid4()),
                'PCtype': pctype,
                'PCname': pcname,
                'PCdesc': pcdesc,
                'ParentPCid': parentpcid,
                'PCpic': pcpic,
                'PCsort': pcsort,
                'PCtopPic': data.get('pctoppic')
            })
            s.add(category_instance)
        return Success('创建成功', {'pcid': category_instance.PCid})

    @admin_required
    def delete(self):
        data = parameter_required(('pcid', ))
        pcid = data.get('pcid')
        with self.sproduct.auto_commit() as s:
            product_category_instance = s.query(ProductCategory).filter_by_({'PCid': pcid}).first_('该分类不存在')
            product_category_instance.isdelete = True
            s.add(product_category_instance)
            s.query(Products).filter_(Products.PCid == product_category_instance.PCid).update({
                'PRstatus': ProductStatus.off_shelves.value,
                'PCid': None
            }, synchronize_session=False)
            # else:
            #     parent_catetgory_instance = s.query(ProductCategory).filter_by_({'PCid': parent_catetgory_id}).first_()
            #     if not parent_catetgory_instance:   # 父级目录已删除
            #         s.query(Products).filter_(Products.PCid.in_(sub_ids)).update({
            #             'PCid': 'null'
            #         }, synchronize_session=False)
            #     else:
            #         pass
            #         s.query(Products).filter_by_({
            #             'PCid': pcid
            #         }).update({
            #             'PCid': parent_catetgory_id
            #         }, synchronize_session=False)
        return Success('删除成功')

    def update(self):
        """更新分类"""
        data = parameter_required(('pcid', 'pcdesc', 'pcname', 'pcpic'))
        pcdesc = data.get('pcdesc')
        pcname = data.get('pcname')
        pcpic = data.get('pcpic')
        parentpcid = data.get('parentpcid')
        # pcsort = self._check_sort(data.get('pcid'), data.get('pcsort', 1))
        pcsort = int(data.get('pcsort', 1))
        pctoppic = data.get('pctoppic')
        with db.auto_commit():
            current_category = ProductCategory.query.filter(
                ProductCategory.isdelete == False,
                ProductCategory.PCid == data.get('pcid')
            ).first_('分类不存在')
            pcsort = self._check_sort(current_category.PCtype, pcsort, parentpcid)
            if parentpcid:
                parent_cat = ProductCategory.query.filter(
                    ProductCategory.isdelete == False,
                    ProductCategory.PCid == parentpcid
                ).first_('指定上级目录不存在')
                current_category.PCtype = parent_cat.PCtype + 1
            else:
                current_category.PCtype = 1
            current_category.update({
                'PCname': pcname,
                'PCdesc': pcdesc,
                'ParentPCid': parentpcid,
                'PCsort': pcsort,
                'PCpic': pcpic,
                'PCtopPic': pctoppic
            }, null='not ignore')
            db.session.add(current_category)
        return Success('更新成功')

    def _sub_category(self, category, deep, parent_ids=()):
        """遍历子分类"""
        parent_ids = list(parent_ids)
        try:
            deep = int(deep)
        except TypeError as e:
            raise ParamsError()
        if deep <= 0:
            del parent_ids
            return
        deep -= 1
        pcid = category.PCid
        if pcid not in parent_ids:
            subs = self.sproduct.get_categorys({'ParentPCid': pcid})
            if subs:
                parent_ids.append(pcid)
                category.fill('subs', subs)
                for sub in subs:
                    self._sub_category(sub, deep, parent_ids)

    def _check_sort(self, pctype, pcsort, parentpcid=None):
        count_pc = ProductCategory.query.filter_by_(PCtype=pctype, ParentPCid=parentpcid).count()
        if pcsort < 1:
            return 1
        if pcsort > count_pc:
            return count_pc
        return pcsort
