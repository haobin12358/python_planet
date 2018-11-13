# -*- coding: utf-8 -*-
from planet.common.base_service import close_session, SBase
from planet.models import User
from planet.models import News, NewsComment, NewsFavorite, NewsImage, NewsVideo, NewsTag


class SNews(SBase):

    @close_session
    def get_news_list(self):
        return self.session.query(News).filter_by_(NEstatus=1).all_with_page()

    @close_session
    def get_news_content(self, nfilter):
        """获取资讯详情"""
        return self.session.query(News).filter_by_(**nfilter).first_()

    @close_session
    def get_news_images(self, neid):
        """获取资讯关联图片"""
        return self.session.query(NewsImage).filter_(NewsImage.NEid == neid, NewsImage.isdelete == False).order_by(
            NewsImage.NIsort.asc(), NewsImage.createtime.asc()).all()

    @close_session
    def get_news_video(self, neid):
        """获取资讯视频"""
        return self.session.query(NewsVideo).filter_(NewsVideo.NEid == neid, NewsVideo.isdelete == False).first()

    @close_session
    def update_pageviews(self, neid, num=1):
        """增加浏览量"""
        return self.session.query(News).filter_by_(NEid=neid).update({News.NEpageviews: News.NEpageviews + num})

    @close_session
    def get_news_comment_count(self, neid):
        """获取资讯评论数"""
        return self.session.query(NewsComment).filter_by_(NEid=neid).count()

    @close_session
    def get_news_favorite_count(self, neid):
        """获取资讯点赞数"""
        return self.session.query(NewsFavorite).filter_by_(NEid=neid).count()

    @close_session
    def news_is_favorite(self, neid, usid):
        """是否已对资讯点赞"""
        return self.session.query(NewsFavorite).filter_by_(NEid=neid, USid=usid).first()

    @close_session
    def get_user_by_id(self, usid):
        return self.session.query(User).filter(User.USid == usid).first_('用户不存在')

