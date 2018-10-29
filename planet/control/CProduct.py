# -*- coding: utf-8 -*-
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
        return Success(data=product)

    def get_produt_list(self):
        pass

    def add_product(self):
        pass

