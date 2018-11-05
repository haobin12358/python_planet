# -*- coding: utf-8 -*-
from datetime import datetime

from sqlalchemy import Column, create_engine, Integer, String, Text, Float, Boolean, orm, DateTime

from planet.common.base_model import Base


class Admin(Base):
    """
    管理员
    """
    __tablename__ = 'Admin'
    ADid = Column(String(64), primary_key=True)
    ADname = Column(String(255), comment='管理员名')
    ADpassword = Column(Text, nullable=False, comment='密码')
    ADheader = Column(Text, comment='头像')
    ADlevel = Column(Integer, default=2, comment='管理员等级，{1: 超级管理员, 2: 普通管理员}')
    ADstatus = Column(Integer, default=0, comment='账号状态，{0:正常, 1: 被冻结, 2: 已删除}')
    ADcreateTime = Column(DateTime, default=datetime.now(), comment='创建时间')


class AdminNotes(Base):
    """
    管理员变更记录
    """
    __tablename__ = 'AdminNotes'
    ANid = Column(String(64), primary_key=True)
    ADid = Column(String(64), nullable=False, comment='管理员id')
    ANcreateTime = Column(DateTime, default=datetime.now(), comment='变更时间')
    ANdoneid = Column(String(64), comment='修改人id')
