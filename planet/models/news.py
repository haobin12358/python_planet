# -*- coding: utf-8 -*-
from sqlalchemy import String, Text, Integer, Boolean
from planet.common.base_model import Base, Column


class News(Base):
    """资讯内容"""
    __tablename__ = 'News'
    NEid = Column(String(64), primary_key=True)
    USid = Column(String(64), nullable=False, comment='发布用户id')
    USname = Column(String(255), comment='用户名')
    USheader = Column(Text, default='用户头像', url=True)
    NEtitle = Column(String(32), nullable=False, comment='标题')
    NEtext = Column(Text, comment='文本内容')
    NEstatus = Column(Integer, default=2, comment='资讯上下架{0: 下架, 1: 上架 2: 审核中}')
    NEpageviews = Column(Integer, default=0, comment='浏览量')
    NEsource = Column(String(64), comment='来源终端')
    COid = Column(Text, comment='优惠券id [coid1, coid2, coid3]')
    PRid = Column(Text, comment='商品id [prid1, prid2, prid3]')
    NEmainpic = Column(String(255), url=True, comment='封面图')
    NEisrecommend = Column(Boolean, default=False, comment='是否推荐到圈子首页轮播')


class NewsImage(Base):
    """资讯图片"""
    __tablename__ = 'NewsImage'
    NIid = Column(String(64), primary_key=True)
    NEid = Column(String(64), nullable=False, comment='资讯id')
    NIimage = Column(String(255), nullable=False, url=True, comment='图片url')
    NIsort = Column(Integer, comment='图片顺序')
    NIthumbnail = Column(String(255), url=True, comment='压缩图')


class NewsVideo(Base):
    """资讯视频"""
    __tablename__ = 'NewsVideo'
    NVid = Column(String(64), primary_key=True)
    NEid = Column(String(64), nullable=False, comment='资讯id')
    NVvideo = Column(String(255), nullable=False, url=True, comment='视频url')
    NVthumbnail = Column(String(255), nullable=False, url=True, comment='视频缩略图')
    NVduration = Column(String(8), nullable=False, default='00:00', comment='视频时长')


class NewsComment(Base):
    """资讯评论"""
    __tablename__ = 'NewsComment'
    NCid = Column(String(64), primary_key=True)
    NEid = Column(String(64), nullable=False, comment='资讯id')
    USid = Column(String(64), nullable=False, comment='评论者id')
    USname = Column(String(255), comment='用户名')
    USheader = Column(Text, default='用户头像', url=True)
    NCtext = Column(String(140), comment='评论内容')
    NCparentid = Column(String(64), comment='回复的父类评论id')
    NCrootid = Column(String(64), comment='回复源评论id')


class NewsCommentFavorite(Base):
    """资讯评论点赞"""
    __tablename__ = 'NewsCommentFavorite'
    NCFid = Column(String(64), primary_key=True)
    NCid = Column(String(64), nullable=False, comment='资讯评论id')
    USid = Column(String(64), nullable=False, comment='点赞用户id')


class NewsFavorite(Base):
    """资讯点赞"""
    __tablename__ = 'NewsFavorite'
    NEFid = Column(String(64), primary_key=True)
    NEid = Column(String(64), nullable=False, comment='资讯id')
    USid = Column(String(64), nullable=False, comment='用户id')


class NewsTrample(Base):
    """资讯点踩"""
    __tablename__ = 'NewsTrample'
    NETid = Column(String(64), primary_key=True)
    NEid = Column(String(64), nullable=False, comment='资讯id')
    USid = Column(String(64), nullable=False, comment='用户id')


class NewsTag(Base):
    """资讯标签关联"""
    __tablename__ = 'NewsTag'
    NTid = Column(String(64), primary_key=True)
    NEid = Column(String(64), nullable=False, comment='资讯id')
    ITid = Column(String(64), nullable=False, comment='标签id')


