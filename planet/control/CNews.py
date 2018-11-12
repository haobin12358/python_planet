# -*- coding: utf-8 -*-
from flask import request
from planet.common.error_response import TokenError
from planet.common.params_validates import parameter_required
from planet.common.request_handler import gennerc_log
from planet.common.success_response import Success
from planet.common.token_handler import token_required
from planet.service.SNews import SNews


class CNews(object):
    def __init__(self):
        self.snews = SNews()

    @token_required
    def get_all_news(self):
        usid = request.user.id
        user = self.snews.get_user_by_id(usid)
        gennerc_log('get user is {0}'.format(user))
        if not user:
            raise TokenError('token error')
        parameter_required(('page_num', 'page_size'))
        news_list = self.snews.get_news_list()
        for news in news_list:
            news.fields = ['NEtitle', 'NEpageviews']
            self.snews.update_pageviews(news.NEid)
            is_favorite = self.snews.news_is_favorite(news.NEid, usid)
            favorite = 1 if is_favorite else 0
            news.fill('is_favorite', favorite)
            commentnumber = self.snews.get_news_comment_count(news.NEid)
            news.fill('commentnumber', commentnumber)
            favoritnumber = self.snews.get_news_favorite_count(news.NEid)
            news.fill('favoritnumber', favoritnumber)
            image_list = self.snews.get_news_images(news.NEid)
            if image_list:
                mainpic = image_list[0].NIimage
                showtype = 'picture'
                news.fill('mainpic', mainpic)
            else:
                video = self.snews.get_news_video(news.NEid)
                if video:
                    video_source = video.NVvideo
                    showtype = 'video'
                    news.fill('video', video_source)
                else:
                    netext = news.NEtext[:120]
                    news.fill('netext', netext)
                    showtype = 'text'
            news.fill('showtype', showtype)
        return Success(data=news_list)
