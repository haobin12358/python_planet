# -*- coding: utf-8 -*-
from sqlalchemy import Integer, String, Text, Float, Boolean, DateTime, DECIMAL
from sqlalchemy.dialects.mysql import LONGTEXT
from planet.common.base_model import Base, Column

class CompanyMessage(Base):
    """
    公司公告
    """
    __tablename__ = "CompanyMessage"
    CMid = Column(String(64), primary_key=True)
    CMtitle = Column(String(255), nullable=False, comment="公告标题")
    CMmessage = Column(LONGTEXT, nullable=False, comment="公告详情")
    CMindex = Column(Integer, nullable=False, default=0, comment="公告是否展示首页")
    CMreadnum = Column(Integer, default=0, comment="公告阅读量")

class UserWords(Base):
    """
    官网留言
    """
    __tablename__ = "UserWords"
    UWid = Column(String(64), primary_key=True)
    UWmessage = Column(Text, nullable=False, comment="留言内容")
    UWname = Column(String(64), comment="留言人姓名")
    UWtelphone = Column(String(14), comment="留言人联系方式")
    UWemail = Column(String(128), comment="留言人邮箱")