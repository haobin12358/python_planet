# -*- coding: utf-8 -*-
from sqlalchemy import Integer, String, Boolean, Text
from sqlalchemy.dialects.mysql import LONGTEXT

from planet.common.base_model import Base, Column


# class IndexBrand(Base):
#     """
#     首页显示的品牌
#     """
#     __tablename__ = 'IndexBrand'
#     IBid = Column(String(64), primary_key=True)
#     PBid = Column(String(64), nullable=False, comment='商品品牌')
#     IBsort = Column(Integer, comment='顺序标志')
#
#
# class IndexBrandProduct(Base):
#     """
#     品牌推荐展示的商品
#     """
#     __tablename__ = 'IndexBrandProduct'
#     IBPid = Column(String(64), primary_key=True)
#     PRid = Column(String(64), primary_key=True, comment='商品')
#     IBPsort = Column(Integer, comment='顺序')


class IndexBanner(Base):
    """
    首页的轮播图
    """
    __tablename__ = 'IndexBanner'
    IBid = Column(String(64), primary_key=True)
    # PRid = Column(String(64), nullable=False, comment='跳转商品')
    IBpic = Column(String(255), nullable=False, comment='图片', url=True)
    IBsort = Column(Integer, comment='顺序')
    IBshow = Column(Boolean, default=True, comment='是否展示')
    contentlink = Column(LONGTEXT, comment='跳转链接')


class HypermarketIndexBanner(Base):
    """
    商品页的轮播图
    """
    __tablename__ = 'HypermarketIndexBanner'
    HIBid = Column(String(64), primary_key=True)
    # PRid = Column(String(64), nullable=False, comment='跳转商品')
    HIBpic = Column(String(255), nullable=False, comment='图片', url=True)
    HIBsort = Column(Integer, comment='顺序')
    HIBshow = Column(Boolean, default=True, comment='是否展示')
    contentlink = Column(LONGTEXT, comment='跳转链接')


class MiniProgramBanner(Base):
    """小程序轮播图"""
    __tablename__ = 'MiniProgramBanner'
    MPBid = Column(String(64), primary_key=True)
    ADid = Column(String(64), comment='创建者id')
    MPBpicture = Column(Text, nullable=False, comment='图片', url=True)
    MPBsort = Column(Integer, comment='顺序')
    MPBshow = Column(Boolean, default=True, comment='是否展示')
    MPBposition = Column(Integer, default=0, comment='轮播图位置 0: 首页, 1: 出游')
    contentlink = Column(LONGTEXT, comment='跳转链接')


class Entry(Base):
    """
    活动入口
    """
    __tablename__ = 'Entry'
    ENid = Column(String(64), primary_key=True)
    ENpic = Column(Text, url=True, comment='活动入口图')
    ENshow = Column(Boolean, default=False, comment='是否展示')
    contentlink = Column(LONGTEXT, comment='跳转链接')
    ENtype = Column(Integer, default= 0, comment='位置 0 最上面 1 中间 2 最下面左边 3 最下面右边')
    ACid = Column(String(64), comment='创建人id')
#
# class IndexHotProduct(Base):
#     """首页显示的热卖商品"""
#     __tablename__ = 'IndexHotProduct'
#     IHPid = Column(String(64), primary_key=True)
#     PRid = Column(String(64), nullable=False, comment='商品id')
#     IHPsort = Column(Integer, comment='顺序标志')
#