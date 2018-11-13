# -*- coding: utf-8 -*-
from planet.common.base_service import close_session, SBase
from planet.models import User, Items
from planet.models import News, NewsComment, NewsFavorite, NewsImage, NewsVideo, NewsTag


class SNews(SBase):

    @close_session
    def get_news_list(self, args):
        """获取资讯列表"""
        return self.session.query(News).filter(News.isdelete == False).outerjoin(
            NewsTag, NewsTag.NEid == News.NEid).filter_(*args).order_by(
            News.createtime.desc()).all_with_page()

    @close_session
    def get_news_content(self, nfilter):
        """获取资讯详情"""
        return self.session.query(News).filter_by_(**nfilter).first_()

    @close_session
    def get_news_images(self, neid):
        """获取资讯关联图片"""
        return self.session.query(NewsImage).filter_by_(NEid=neid).order_by(
            NewsImage.NIsort.asc(), NewsImage.createtime.asc()).all()

    @close_session
    def get_news_video(self, neid):
        """获取资讯视频"""
        return self.session.query(NewsVideo).filter_by_(NEid=neid).first()

    @close_session
    def get_news_tags(self, neid):
        """获取资讯关联标签"""
        return self.session.query(NewsTag).filter_by_(NEid=neid).all()

    @close_session
    def get_item_list(self, args, order=()):
        """获取资讯对应的标签"""
        return self.session.query(Items).outerjoin(NewsTag, Items.ITid == NewsTag.ITid).filter_(
            *args
        ).order_by(*order).all()

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

