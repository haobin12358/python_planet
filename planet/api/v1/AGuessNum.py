# -*- coding: utf-8 -*-
from planet.common.base_resource import Resource
from planet.control.CGuessNum import CGuessNum


class AGuessNum(Resource):
    def __init__(self):
        self.cguessnum = CGuessNum()

    def post(self, guess_num):
        apis = {
            'create': self.cguessnum.creat
        }
        return apis

    def get(self, guess_num):
        apis = {
            'get': self.cguessnum.get,
            'history_join': self.cguessnum.history_join,
        }
        return apis
