# -*- coding: utf-8 -*-
from planet.control.CCollection import CCollection
from planet.common.base_resource import Resource


class ACollection(Resource):

    def __init__(self):
        self.collection = CCollection()

    def post(self, collection):
        apis ={
            'collect':self.collection.collect
        }
        return apis