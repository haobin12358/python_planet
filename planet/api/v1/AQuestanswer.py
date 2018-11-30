# -*- coding: utf-8 -*-
from planet.common.base_resource import Resource
from planet.control.CQuestanswer import CQuestanswer


class AQuestanswer(Resource):

    def __init__(self):
        self.qa = CQuestanswer()

    def post(self, qa):
        apis = {
            'add_questoutline': self.qa.add_questoutline,
            'add_questanswer': self.qa.add_questanswer,
        }
        return apis

    def get(self, qa):
        apis = {
            'get_all_quest': self.qa.get_all_quest,
            'get_answer': self.qa.get_answer,
            'get_all': self.qa.get_all,
        }
        return apis
