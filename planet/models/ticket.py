# -*- coding: utf-8 -*-
from sqlalchemy import orm, Integer, String, Text, DateTime, DECIMAL
from sqlalchemy.dialects.mysql import LONGTEXT
from planet.common.base_model import Base, Column


class UserMaterialFeedback(Base):
    """
    素材反馈
    """
    __tablename__ = 'UserMaterialFeedback'
    UMFid = Column(String(64), primary_key=True)
    UMFdetails = Column(Text)
    UMFlocation = Column(Text)
    UMFstatus = Column(Integer, default=0, comment='0 未退押金 1 已退')
    TIid = Column(String(64), comment='门票id')
    USid = Column(String(64), comment='用户id')


class MaterialFeedbackLinkage(Base):
    """
    联动平台分享凭证
    """
    __tablename__ = 'MaterialFeedbackLinkage'
    MFLid = Column(String(64), primary_key=True)
    UMFid = Column(String(64), comment='反馈id')
    LIid = Column(String(64), comment='联动平台id')
    MFLimg = Column(Text, url=True, comment='截图')
    MFLlink = Column(Text, comment='链接')


class Ticket(Base):
    """票务实体"""
    __tablename__ = 'Ticket'
    TIid = Column(String(64), primary_key=True)
    ADid = Column(String(64), comment='创建者')
    TIname = Column(String(256), nullable=False, comment='票名')
    TIimg = Column(Text, url=True, comment='封面图')
    TIstartTime = Column(DateTime, comment='开抢时间')
    TIendTime = Column(DateTime, comment='结束时间')
    TIrules = Column(Text, comment='规则')
    TIcertificate = Column(Text, url=True, comment='景区资质凭证')
    TIdetails = Column(Text, comment='票详情')
    TIprice = Column(DECIMAL(precision=28, scale=2), comment='票价')
    TIdeposit = Column(DECIMAL(precision=28, scale=2), default=1, comment='抢票押金')
    TIstatus = Column(Integer, default=0, comment='抢票状态 0: 未开始, 1: 抢票中, 2: 中止 , 3: 已结束')
    TInum = Column(Integer, default=1, comment='数量')
    TIrewardnum = Column(LONGTEXT, comment='中奖号码')
    TIabbreviation = Column(String(200), comment='列表页封面的简称')
    TIcategory = Column(Text, comment='列表页显示的类型')

    @orm.reconstructor
    def __init__(self):
        super(Ticket, self).__init__()
        self.hide('TIcategory', 'TIrewardnum')


class TicketDeposit(Base):
    """票押金记录"""
    __tablename__ = 'TicketDeposit'
    TDid = Column(String(64), primary_key=True)
    TSOid = Column(String(64), comment='购票记录')
    TDdeposit = Column(DECIMAL(precision=28, scale=2), comment='金额')
    TDtype = Column(Integer, default=0, comment='押金类型 0:抢票押金 1: 补交剩余的押金')
    OPayno = Column(String(64), nullable=False, comment='支付流水号')


class TicketsOrder(Base):
    """购票记录"""
    __tablename__ = 'TicketsOrder'
    TSOid = Column(String(64), primary_key=True)
    USid = Column(String(64), comment='用户')
    TIid = Column(String(64), comment='票id')
    TSOcode = Column(Integer, comment='抢票码')
    TSOstatus = Column(Integer, default=0, comment='状态：-1：未中奖 0: 待开奖 1：(已中奖)待补押金 2：已出票')


class Linkage(Base):
    """
    联动平台
    """
    __tablename__ = 'Linkage'
    LIid = Column(String(64), primary_key=True)
    LIname = Column(String(256))
    LIicon = Column(Text, url=True)
    LIstatus = Column(Integer, default=0, comment='0 可用 1 不可用')
    LIshareType = Column(Integer, default=0, comment='0 仅截图 1 截图+链接')


class TicketLinkage(Base):
    """
    门票联动记录
    """
    __tablename__ = 'TicketLinkage'
    TLid = Column(String(64), primary_key=True)
    LIid = Column(String(64))
    TIid = Column(String(64))
