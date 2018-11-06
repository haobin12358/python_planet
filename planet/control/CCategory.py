# -*- coding: utf-8 -*-
from planet.common.error_response import ParamsError
from planet.common.params_validates import parameter_required
from planet.common.success_response import Success
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

    def create(self):
        """创建分类"""
        pass

    def _sub_category(self, category, deep):
        """遍历子分类"""
        try:
            deep = int(deep)
        except TypeError as e:
            raise ParamsError()
        print('hello')
        if deep <= 0:
            return
        deep -= 1
        subs = self.sproduct.get_categorys({'ParentPCid': category.PCid})
        if subs:
            category.fill('subs', subs)
            for sub in subs:
                self._sub_category(sub, deep)

