# -*- coding: utf-8 -*-
from datetime import date

from sqlalchemy import Integer, String, Date, Float, Text, DateTime, Boolean
from planet.common.base_model import Base, Column


class Activity(Base):
    """活动列表控制"""
    __tablename__ = 'Activity'
    ACid = Column(Integer, primary_key=True)
    ACbackGround = Column(String(255), nullable=False, url=True, comment='列表页背景图')
    ACtopPic = Column(String(255), nullable=False, url=True, comment='顶部图 ')
    ACbutton = Column(String(16), default='立即参与', comment='按钮文字')
    ACtype = Column(Integer, default=0, unique=True, index=True, comment='类型 0: 新人 1 猜数字 2 魔术礼盒 3 免费试用')
    ACshow = Column(Boolean, default=True, comment='是否开放')
    ACdesc = Column(String(255), comment='活动描述')
    ACname = Column(String(16), nullable=False, comment='名字')
    ACsort = Column(Integer, comment='顺序标志')


class TrialCommodity(Base):
    """试用商品"""
    __tablename__ = 'TrialCommodity'
    TCid = Column(String(64), primary_key=True)
    TCtitle = Column(String(255), nullable=False, comment='标题')
    TCdescription = Column(Text, comment='商品描述')
    TCdeposit = Column(Float, nullable=False, comment='押金')
    TCdeadline = Column(Integer, nullable=False, default=31, comment='押金期限{单位:天}')
    TCfreight = Column(Float, default=0, comment='运费')
    TCstocks = Column(Integer, comment='库存')
    TCsalesValue = Column(Integer, default=0, comment='销量')
    TCstatus = Column(Integer, default=0, comment='状态  0 正常, 10 下架, 20 审核中')
    TCmainpic = Column(String(255), comment='主图', url=True)
    TCattribute = Column(Text, comment='商品属性 ["网络","颜色","存储"]')
    TCdesc = Column(Text, comment='商品详细介绍', url_list=True)
    TCremarks = Column(String(255), comment='备注')
    CreaterId = Column(String(64), nullable=False, comment='创建者')
    PBid = Column(String(64), comment='品牌id')


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
    SKUprice = Column(Float, nullable=False, comment='价格')
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
    SKUid = Column(String(64), nullable=False, comment='当日奖品')
    PRid = Column(String(64), nullable=False, comment='当日奖品')
    Price = Column(Float, nullable=False, comment='当日价格')


class CorrectNum(Base):
    """正确数字"""
    __tablename__ = 'CorrectNum'
    CNid = Column(String(64), primary_key=True)
    CNnum = Column(String(16), nullable=False, comment='正确的数字')
    CNdate = Column(Date, nullable=False, comment='日期')


class GuessAwardFlow(Base):
    """猜数字中奖和领奖记录"""
    __tablename__ = 'GuessAwardFlow'
    GAFid = Column(String(64), primary_key=True)
    GNid = Column(String(64), nullable=False, unique=True, comment='个人参与记录')
    GAFstatus = Column(Integer, default=0, comment='领奖状态 0 待领奖, 10 已领取 20 过期')


class GuessNumAwardApply(Base):
    """申请参与猜数字"""
    __tablename__ = 'GuessNumAward'
    GNAAid = Column(String(64), primary_key=True)
    SUid = Column(String(64), nullable=False, comment='供应商id')
    SKUid = Column(String(64), nullable=False, comment='申请参与的sku')
    PRid = Column(String(64), nullable=False, comment='商品id')
    GNAAstarttime = Column(Date, nullable=False, comment='申请参与的起始时间')
    GNAAendtime = Column(Date, nullable=False, comment='申请参与的结束时间')
    SKUprice = Column(Float, default=0.01, comment='参与价格')
    GNAAstatus = Column(Integer, default=0, comment='申请状态, 0: 未处理, -10: 拒绝, 10: 通过')
    AgreeStartime = Column(Date, comment='最终确认起始时间')  # 同意之后不可为空
    AgreeEndtime = Column(Date, comment='最终确认结束时间')


# 魔术礼盒
# class MagicBox(Base):
#     __tablename__ = 'MagicBox'
#     MBid = Column(String(64), primary_key=True)
#

class MagicBoxApply(Base):
    __tablename__ = 'MagicBoxApply'
    MBAid = Column(String(64), primary_key=True)
    SUid = Column(String(64), nullable=False, comment='供应商id')
    SKUid = Column(String(64), nullable=False, comment='申请参与的sku')
    PRid = Column(String(64), nullable=False, comment='商品id')
    MBAstarttime = Column(Date, nullable=False, comment='申请参与的起始时间')
    MBAendtime = Column(Date, nullable=False, comment='申请参与的结束时间')
    SKUprice = Column(Float, nullable=False, comment='原价')
    SKUminPrice = Column(Float, nullable=False, comment='最低价')
    Gearsone = Column(String(64), nullable=False, comment='第一档 [2-1, 230-3]')
    Gearstwo = Column(String(64), nullable=False, comment='第二档 [2-1, 230-3]')
    Gearsthree = Column(String(64), nullable=False, comment='第三档 [2-1, 230-3]')
    MBAstatus = Column(Integer, default=0, comment='申请状态, 0: 未处理, -10: 拒绝, 10: 通过')
    AgreeStartime = Column(Date, comment='最终确认起始时间')  # 同意之后不可为空
    AgreeEndtime = Column(Date, comment='最终确认结束时间')





