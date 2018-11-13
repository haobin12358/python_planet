# -*- coding: utf-8 -*-
from planet.common.params_validates import parameter_required
from planet.common.success_response import Success
from planet.models.trade import LogisticsCompnay
from planet.service.STrade import STrade


class CLogistic:
    def __init__(self):
        self.sorder = STrade()

    def list_company(self):
        data = parameter_required()
        kw = data.get('kw') or ''
        logistics = self.sorder.get_logistics_list([
            LogisticsCompnay.LCname.contains(kw)
        ])
        return Success(data=logistics)


