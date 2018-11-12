# -*- coding: utf-8 -*-
from planet.models.news import News, NewsComment, NewsFavorite, NewsImage, NewsVideo, NewsTag
from sqlalchemy import or_


class SNews():

    def get_all_news(self):
        return self.session.query(News).filter_by_().all_with_page()

    def get_news_content(self):
        pass

    def get_news_images(self, neid):
        """获取资讯关联图片"""
        return self.session.query(NewsImage).filter_by_(NEid=neid).order_by(
            or_(NewsImage.NIsort.asc(), NewsImage.createtime.asc())).all()

    def get_news_video(self, neid):
        """获取资讯视频"""
        return self.session.query(NewsVideo).filter_by_(NEid=neid).first()

    def update_pageviews(self, neid, num=1):
        """增加浏览量"""
        return self.session.query(News).filter_by_(NEid=neid).update({News.NEpageviews: News.NEpageviews + num})

    def get_news_comment_count(self, neid):
        """获取资讯评论数"""
        return self.session.query(NewsComment).filter_by_(NEid=neid).count()

    def get_news_favorite_count(self, neid):
        """获取资讯点赞数"""
        return self.session.query(NewsFavorite).filter_by_(NEid=neid).count()

    def news_is_favorite(self, neid, usid):
        """是否已对资讯点赞"""
        return self.session.query(NewsFavorite).filter_by_(NEid=neid, USid=usid).first()



