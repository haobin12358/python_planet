# -*- coding: utf-8 -*-
from planet.common.base_resource import Resource
from planet.control.CNews import CNews


class ANews(Resource):
    def __init__(self):
        self.cnews = CNews()

    def post(self, news):
        apis = {
            'create_news': self.cnews.create_news,

        }
        return apis

    def get(self, news):
        apis = {
            'get_all_news': self.cnews.get_all_news,
            'get_news_content': self.cnews.get_news_content,

        }
        return apis

