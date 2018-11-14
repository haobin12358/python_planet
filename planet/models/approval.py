# -*- coding: utf-8 -*-
from datetime import datetime

from sqlalchemy import create_engine, Integer, String, Text, Float, Boolean, orm, DateTime, DECIMAL

from planet.common.base_model import Base, Column


class Approval(Base):
    """审批流"""
    __tablename__ = 'Approval'
    AVid = Column(String(64), primary_key=True)
    AVname = Column(String(255), nullable=False, comment='审批流名称')
    AVtype = Column(Integer, default=1, comment='审批流类型 1: 成为代理商审批 2:商品上架审批 3:订单退换货审批, 4: 提现审批 5: 用户资讯发布审批')
    AVstartid = Column(String(64), nullable=False, comment='发起人')
    AVlevel = Column(String(64), comment='当前审批人等级')
    AVstatus = Column(Integer, default=1, comment='审批状态 -20已取消 -10 拒绝 0 未审核 10审核通过')
    AVcontent = Column(String(64), comment='待审批的对象')


# 权限
class Permission(Base):
    """审批流处理管理员"""
    __tablename__ = "Permission"
    PEid = Column(String(64), primary_key=True)
    ADid = Column(String(64), nullable=False, comment='管理员id')
    PEtype = Column(Integer, nullable=False, comment='审批流类型 1: 成为代理商审批 2:商品上架审批 3:订单退换货审批, 4: 提现审批 5: 用户资讯发布审批')
    PELevel = Column(Integer, nullable=False, comment='审批层级 1-10')


class ApprovalNotes(Base):
    """审批流处理记录"""
    __tablename__= 'ApprovalNotes'
    ANid = Column(String(64), primary_key=True)
    AVid = Column(String(64), comment='审批流id')
    AVadname = Column(Text, comment='处理人姓名')
    ADid = Column(String(64), comment='处理人id')
    ANaction = Column(Integer, default=1, comment='审批意见 1 同意,0 提交 -1：拒绝')
    ANabo = Column(Text, comment='审批备注')
