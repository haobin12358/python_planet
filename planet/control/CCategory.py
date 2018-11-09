# -*- coding: utf-8 -*-
import uuid

from planet.common.error_response import ParamsError, StatusError
from planet.common.params_validates import parameter_required
from planet.common.success_response import Success
from planet.common.token_handler import token_required
from planet.models import ProductCategory, Products
from planet.service.SProduct import SProducts


class CCategory(object):
    def __init__(self):
        self.sproduct = SProducts()

    def get_category(self):
        """获取类目"""
        data = parameter_required()
        up = data.get('up', '')
        deep = data.get('deep', 0)  # 深度
        categorys = self.sproduct.get_categorys({'ParentPCid': up})
        for category in categorys:
            self._sub_category(category, deep)
        return Success(data=categorys)

    @token_required
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
                'PCsort': pcsort
            })
            s.add(category_instance)
        return Success('创建成功', {'pcid': category_instance.PCid})

    def delete(self):
        data = parameter_required(('pcid', ))
        pcid = data.get('pcid')
        with self.sproduct.auto_commit() as s:
            # 删除分类
            product_category_instance = s.query(ProductCategory).filter_by_({'PCid': pcid}).first_('该分类不存在')
            product_category_instance.isdelete = True
            s.add(product_category_instance)
            # 该分类下的商品挂在上一级
            up_catetgory_id = product_category_instance.ParentPCid
            if not up_catetgory_id:
                # 如果没有父级目录 todo
                #
                raise StatusError()
            else:
                # 如果父级目录不存在 todo
                up_catetgory_instance = s.query(ProductCategory).filter_by_({'PCid': up_catetgory_id}).first_()
                if not up_catetgory_instance:
                    raise StatusError()
                s.query(Products).filter_by_({
                    'PCid': pcid
                }).update({
                    'PCid': up_catetgory_id
                })
        return Success('删除成功')

    def _sub_category(self, category, deep):
        """遍历子分类"""
        try:
            deep = int(deep)
        except TypeError as e:
            raise ParamsError()
        if deep <= 0:
            return
        deep -= 1
        subs = self.sproduct.get_categorys({'ParentPCid': category.PCid})
        if subs:
            category.fill('subs', subs)
            for sub in subs:
                self._sub_category(sub, deep)

