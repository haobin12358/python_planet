# -*- coding: utf-8 -*-
from planet.common.base_resource import Resource
from planet.control.CNews import CNews


class ANews(Resource):
    def __init__(self):
        self.cnews = CNews()

    def post(self, news):
        apis = {

        }
        return apis

    def get(self, news):
        apis = {
            'get_all_news': self.cnews.get_all_news,

        }
        return apis

