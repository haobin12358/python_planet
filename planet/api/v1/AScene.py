# -*- coding: utf-8 -*-
from planet.common.base_resource import Resource
from planet.control.CScene import CScene


class AScene(Resource):
    """场景"""
    def __init__(self):
        self.cscene = CScene()

    def get(self, scene):
        apis = {
            'list': self.cscene.list
        }
        return apis

    def post(self, scene):
        apis = {
            'create': self.cscene.create
        }
        return apis
