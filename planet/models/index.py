# -*- coding: utf-8 -*-
from sqlalchemy import Column, Integer, String

from planet.common.base_model import Base


class IndexProductBrand(Base):
    """
    首页显示的品牌
    """
    __tablename__ = 'IndexProductBrand'
    IPBid = Column(String(64), primary_key=True)
    PBid = Column(String(64), nullable=False, comment='商品品牌')
    IPBsort = Column(Integer, comment='顺序标志')


class IndexProductBrandItem(Base):
    """
    品牌推荐展示的商品
    """
    __tablename__ = 'IndexProductBrandItem'
    IPBIid = Column(String(64), primary_key=True)
    PRid = Column(String(64), primary_key=True, comment='商品')
    IPBIsort = Column(Integer, comment='顺序')


class IndexBanner(Base):
    """
    首页的轮播图
    """
    __tablename__ = 'IndexBanner'
    IBid = Column(String(64), primary_key=True)
    PRid = Column(String(64), nullable=False, comment='跳转商品')
    IBpic = Column(String(255), nullable=False, comment='图片')
    IBsort = Column(Integer, comment='顺序')



