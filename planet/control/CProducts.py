# -*- coding: utf-8 -*-
from planet.common.error_response import NotFound, ParamsError
from planet.common.params_validates import parameter_required
from planet.common.success_response import Success
from planet.service.SProduct import SProducts


class CProducts:
    def __init__(self):
        self.sproduct = SProducts()

    def get_product(self):
        data = parameter_required(('prid', ))
        prid = data.get('prid')
        product = self.sproduct.get_product_by_prid(prid)
        if not product:
            return NotFound()
        return Success(data=product)

    def get_produt_list(self):
        pass

    def add_product(self):
        pass


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
        return Success(categorys)

    def _sub_category(self, category, deep):
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
            category.fill(subs, 'sub')
            for sub in subs:
                self._sub_category(sub, deep)
        # while len(queue) > 0:
        #     cat = queue.pop(0)
        #     sub = self.sproduct.get_categorys({'ParentPCid': cat.PCid})
        #     if sub:
        #         cat.fill(sub, 'sub')
        #         queue.extend(sub)




