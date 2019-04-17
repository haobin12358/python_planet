# -*- coding: utf-8 -*-
from planet.common.base_resource import Resource
from planet.control.CSku import CSku


class ASku(Resource):
    def __init__(self):
        self.csku = CSku()

    def post(self, sku):
        apis = {
            'create': self.csku.add,
            'update': self.csku.update,
        }
        return apis

