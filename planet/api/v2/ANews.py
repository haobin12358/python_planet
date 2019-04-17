# -*- coding: utf-8 -*-
from planet.common.base_resource import Resource
from planet.control.CNews import CNews


class ANews(Resource):
    def __init__(self):
        self.cnews = CNews()

    def post(self, news):
        apis = {
            'create_news': self.cnews.create_news,
            'favorite_news': self.cnews.news_favorite,
            'create_comment': self.cnews.create_comment,
            'favorite_comment': self.cnews.comment_favorite,
            'del_comment': self.cnews.del_comment,
            'news_shelves': self.cnews.news_shelves,
            'update_news': self.cnews.update_news,
            'del_news': self.cnews.del_news,
        }
        return apis

    def get(self, news):
        apis = {
            'get_all_news': self.cnews.get_all_news,
            'get_news_content': self.cnews.get_news_content,
            'get_news_comment': self.cnews.get_news_comment,
            'banner': self.cnews.get_news_banner,

        }
        return apis

