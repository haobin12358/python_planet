# -*- coding: utf-8 -*-
from datetime import date, datetime

from sqlalchemy import Integer, String, Date, Float, Text
from planet.common.base_model import Base, Column


class TrialCommodity(Base):
    """试用商品"""
    __tablename__ = 'TrialCommodity'
    TCid = Column(String(64), primary_key=True)
    TCtitle = Column(String(255), nullable=False, comment='标题')
    TCdescription = Column(Text, comment='商品描述')
    TCdeposit = Column(Float, nullable=False, comment='押金')
    TCdeadline = Column(Integer, nullable=False, default=30, comment='押金期限{单位:天}')
    PRfreight = Column(Float, default=0, comment='运费')
    TCstocks = Column(Integer, comment='库存')
    TCsalesValue = Column(Integer, default=0, comment='销量')
    TCstatus = Column(Integer, default=0, comment='状态  0 正常, 10下架')
    TCmainpic = Column(String(255), comment='主图', url=True)
    TCattribute = Column(Text, comment='商品属性 ["网络","颜色","存储"]')
    TCdesc = Column(Text, comment='商品详细介绍', url_list=True)
    TCremarks = Column(String(255), comment='备注')
    CreaterId = Column(String(64), nullable=False, comment='创建者')


class TrialCommodityImage(Base):
    """试用商品图片"""
    __tablename__ = 'TrialCommodityImage'
    TCIid = Column(String(64), primary_key=True)
    TCid = Column(String(64), nullable=False, comment='试用商品id')
    TCIpic = Column(String(255), nullable=False, comment='商品图片', url=True)
    TCIsort = Column(Integer, comment='顺序')


class TrialCommoditySku(Base):
    """试用商品SKU"""
    __tablename__ = 'TrialCommoditySku'
    SKUid = Column(String(64), primary_key=True)
    TCid = Column(String(64), nullable=False, comment='试用商品id')
    SKUpic = Column(String(255), nullable=False, comment='图片', url=True)
    SKUattriteDetail = Column(Text, comment='sku属性信息 ["电信","白","16G"]')
    SKUstock = Column(Integer, comment='库存')


class TrialCommoditySkuValue(Base):
    """商品分类sku属性名"""
    __tablename__ = 'TrialCommoditySkuValue'
    TSKUid = Column(String(64), primary_key=True)
    PSKUvalue = Column(Text, comment='属性名["color", "尺寸"]')


class GuessNum(Base):
    """猜数字 参与记录"""
    __tablename__ = 'GuessNum'
    GNid = Column(String(64), primary_key=True)
    GNnum = Column(String(16), nullable=False, comment='猜测的数字')
    USid = Column(String(64), nullable=False, comment='用户id')
    GNdate = Column(Date, default=date.today, comment='参与的日期')


class CorrectNum(Base):
    """奖品和正确数字"""
    __tablename__ = 'CorrectNum'
    CNid = Column(String(64), primary_key=True)
    CNnum = Column(String(16), nullable=False, comment='正确的数字')
    CNdate = Column(Date, nullable=False, comment='日期')
    SKUid = Column(String(64), nullable=False, comment='奖励sku')


class GuessAwardFlow(Base):
    """猜数字中奖和领奖记录"""
    __tablename__ = 'GuessAwardFlow'
    GAFid = Column(String(64), primary_key=True)
    GNid = Column(String(64), nullable=False, unique=True, comment='个人参与记录')
    GAFstatus = Column(Integer, default=0, comment='领奖状态 0 待领奖, 10 已领取 20 过期')


# 魔术礼盒
class MagicBox(Base):
    __tablename__ = 'MagicBox'
    MBid = Column(String(64), primary_key=True)

