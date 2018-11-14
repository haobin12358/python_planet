# -*- coding: utf-8 -*-
from sqlalchemy import String, Text, Integer
from planet.common.base_model import Base, Column


class News(Base):
    """资讯内容"""
    __tablename__ = 'News'
    NEid = Column(String(64), primary_key=True)
    USid = Column(String(64), nullable=False, comment='发布用户id')
    NEtitle = Column(String(32), nullable=False, comment='标题')
    NEtext = Column(Text, comment='文本内容')
    NEstatus = Column(Integer, default=0, comment='资讯上下架{0: 下架, 1: 上架 2: 审核中}')
    NEpageviews = Column(Integer, default=0, comment='浏览量')


class NewsImage(Base):
    """资讯图片"""
    __tablename__ = 'NewsImage'
    NIid = Column(String(64), primary_key=True)
    NEid = Column(String(64), nullable=False, comment='资讯id')
    NIimage = Column(String(255), nullable=False, url=True, comment='图片url')
    NIsort = Column(Integer, comment='图片顺序')
    NIthumbnail = Column(String(255), url=True, comment='预览图')


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
    NCtext = Column(String(140), comment='评论内容')
    NCparentid = Column(String(64), comment='评论回复的资讯id')


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


