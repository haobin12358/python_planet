# -*- coding: utf-8 -*-
from sqlalchemy import Integer, String, Text, Float, DateTime, Boolean, orm, DECIMAL

from planet.common.base_model import Base, Column


class UserMaterialFeedback(Base):
    """
    素材反馈
    """
    __tablename__ = 'UserMaterialFeedback'
    UMFid = Column(String(64), primary_key=True)
    UMFdetails = Column(Text)
    UMimg = Column(Text, url=True)
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
    """
    票务实体
    """
    __tablename__ = 'Ticket'
    TIid = Column(String(64), primary_key=True)
    TIname = Column(String(256))
    TIimg = Column(Text, url=True)
    TIstartTime = Column(DateTime)
    TIendTime = Column(DateTime)
    TIdetails = Column(Text)
    TIdeposit = Column(DECIMAL(precision=28, scale=2))
    TIstatus = Column(Integer, default=0)
    TInum = Column(Integer)


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
