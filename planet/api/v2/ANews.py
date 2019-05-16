# -*- coding: utf-8 -*-
from planet.common.base_resource import Resource
from planet.control.CNews import CNews


class ANews(Resource):
    def __init__(self):
        self.cnews = CNews()

    def post(self, news):
        apis = {
            'create_news': self.cnews.create_news,              # 创建圈子
            'favorite_news': self.cnews.news_favorite,          # 圈子点赞
            'create_comment': self.cnews.create_comment,        # 圈子评论
            'favorite_comment': self.cnews.comment_favorite,    # 评论点赞
            'del_comment': self.cnews.del_comment,              # 删除评论
            'news_shelves': self.cnews.news_shelves,            # 下架圈子
            'update_news': self.cnews.update_news,              # 编辑圈子
            'del_news': self.cnews.del_news,                    # 删除圈子
            'topic': self.cnews.create_topic,                   # 创建话题
            'choose_category': self.cnews.choose_category,      # 选择分类
            'del_topic': self.cnews.del_topic,                  # 删除话题
            'award': self.cnews.news_award,                     # 圈子打赏
        }
        return apis

    def get(self, news):
        apis = {
            'get_all_news': self.cnews.get_all_news,            # 获取圈子列表
            'get_news_content': self.cnews.get_news_content,    # 获取圈子详情
            'get_news_comment': self.cnews.get_news_comment,    # 获取圈子评论
            'banner': self.cnews.get_news_banner,
            'location': self.cnews.get_location,                # 获取定位
            'topic': self.cnews.get_topic,                      # 获取话题
            'search': self.cnews.search,                        # 搜索用户/圈子
            'get_self_news': self.cnews.get_self_news,          # 获取个人圈子列表
            'award': self.cnews.get_news_award,                 # 获取圈子打赏记录

        }
        return apis

