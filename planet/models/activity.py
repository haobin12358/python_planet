# -*- coding: utf-8 -*-
from datetime import date, datetime

from sqlalchemy import Integer, String, Date
from planet.common.base_model import Base, Column


class TrialCommodity(Base):
    """试用商品"""
    __tablename__ = 'TrialCommodity'
    TCid = Column(String(64), primary_key=True)


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

