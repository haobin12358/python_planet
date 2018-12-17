# -*- coding: utf-8 -*-
from sqlalchemy import Integer, String, Boolean

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
    PRid = Column(String(64), nullable=False, comment='跳转商品')
    IBpic = Column(String(255), nullable=False, comment='图片', url=True)
    IBsort = Column(Integer, comment='顺序')
    IBshow = Column(Boolean, default=True, comment='是否展示')

#
# class IndexHotProduct(Base):
#     """首页显示的热卖商品"""
#     __tablename__ = 'IndexHotProduct'
#     IHPid = Column(String(64), primary_key=True)
#     PRid = Column(String(64), nullable=False, comment='商品id')
#     IHPsort = Column(Integer, comment='顺序标志')
#


