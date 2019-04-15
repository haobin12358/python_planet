# -*- coding: utf-8 -*-
from planet.control.CCancelCollection import CCancelCollection
from planet.common.base_resource import Resource


class ACancelCollection(Resource):

    def __init__(self):
        self.cancelled = CCancelCollection()

    def post(self, cancelled):
        apis ={
            'cancel':self.cancelled.cancel
        }
        return apis