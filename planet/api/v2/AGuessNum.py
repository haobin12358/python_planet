# -*- coding: utf-8 -*-
from planet.common.base_resource import Resource
from planet.control.CGuessNum import CGuessNum


class AGuessNum(Resource):
    def __init__(self):
        self.cguessnum = CGuessNum()

    def post(self, guess_num):
        apis = {
            'create': self.cguessnum.creat,
            'recv_award': self.cguessnum.recv_award,
            'apply_award': self.cguessnum.apply_award,
            'update_apply': self.cguessnum.update_apply,
            'shelf_award': self.cguessnum.shelf_award,
            'delete': self.cguessnum.delete_apply,
            'shelves': self.cguessnum.shelves,
        }
        return apis

    def get(self, guess_num):
        apis = {
            'get': self.cguessnum.get,
            'list': self.cguessnum.list,
            'history_join': self.cguessnum.history_join,
            'award_detail': self.cguessnum.award_detail,
            'today_gnap': self.cguessnum.today_gnap,
            'get_discount': self.cguessnum.get_discount_by_skuid,

        }
        return apis
