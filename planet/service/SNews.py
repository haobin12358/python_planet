# -*- coding: utf-8 -*-
from planet.common.base_service import close_session, SBase
from planet.models import News, NewsComment, NewsFavorite, NewsImage, NewsVideo, NewsTag, User, Items, NewsTrample, \
    NewsCommentFavorite, UserCollectionLog


class SNews(SBase):

    @close_session
    def get_news_list(self, args):
        """获取资讯列表"""
        return self.session.query(News).filter(News.isdelete == False).outerjoin(
            NewsTag, NewsTag.NEid == News.NEid).filter_(NewsTag.isdelete == False, *args).order_by(
            News.createtime.desc()).all_with_page()

    @close_session
    def get_collect_news_list(self, args):
        """获取资讯列表"""
        return self.session.query(News).filter(News.isdelete == False).outerjoin(
            NewsTag, NewsTag.NEid == News.NEid).filter_(NewsTag.isdelete == False, *args).order_by(
            UserCollectionLog.createtime.desc()).all_with_page()

    @close_session
    def get_news_list_by_filter(self, args):
        """获取推荐到圈子首页的资讯"""
        return self.session.query(News).filter_by_(**args).all()

    @close_session
    def get_collect_news_list_by_filter(self, args):
        """获取收藏推荐到圈子首页的资讯"""
        return self.session.query(News).filter_by_(**args).order_by(UserCollectionLog.createtime.desc()).all()

    @close_session
    def get_news_content(self, nfilter):
        """获取资讯详情"""
        return self.session.query(News).filter_by_(**nfilter).first_('该资讯不存在或已删除')

    @close_session
    def get_news_comment(self, ncfilter):
        """获取所有资讯评论"""
        return self.session.query(NewsComment).filter(*ncfilter).order_by(NewsComment.createtime.asc()).all_with_page()

    @close_session
    def get_comment_reply_user(self, args):
        """获取回复评论的用户"""
        return self.session.query(User).outerjoin(NewsComment, User.USid == NewsComment.USid).filter_(
            *args).first()

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
    def get_item_list(self, args):
        """获取资讯对应的标签"""
        return self.session.query(Items).outerjoin(NewsTag, Items.ITid == NewsTag.ITid).filter_(
            Items.isdelete == False,
            NewsTag.isdelete == False,
            *args
        ).order_by(Items.ITsort.asc(), Items.createtime.desc()).all()

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
    def get_news_trample_count(self, neid):
        """获取资讯点踩数"""
        return self.session.query(NewsTrample).filter_by_(NEid=neid).count()

    @close_session
    def news_is_favorite(self, neid, usid):
        """是否已对资讯点赞"""
        return self.session.query(NewsFavorite).filter_by_(NEid=neid, USid=usid).first()

    @close_session
    def cancel_favorite(self, neid, usid):
        """取消点赞"""
        return self.session.query(NewsFavorite).filter_by_(NEid=neid, USid=usid).delete_()

    @close_session
    def news_is_trample(self, neid, usid):
        """是否已对资讯点踩"""
        return self.session.query(NewsTrample).filter_by_(NEid=neid, USid=usid).first()

    @close_session
    def cancel_trample(self, neid, usid):
        """取消踩"""
        return self.session.query(NewsTrample).filter_by_(NEid=neid, USid=usid).delete_()

    @close_session
    def comment_is_favorite(self, ncid, usid):
        """评论是否已经点赞"""
        return self.session.query(NewsCommentFavorite).filter_by_(USid=usid, NCid=ncid).first()

    @close_session
    def del_comment(self, ncfilter):
        """删除评论"""
        return self.session.query(NewsComment).filter(ncfilter).delete_()

    @close_session
    def get_user_by_id(self, usid):
        return self.session.query(User).filter(User.USid == usid).first_('用户不存在')
