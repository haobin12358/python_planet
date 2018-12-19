# -*- coding: utf-8 -*-
from sqlalchemy import Integer, String, Text

from planet.common.base_model import Base, Column


class Approval(Base):
    """审批流"""
    __tablename__ = 'Approval'
    AVid = Column(String(64), primary_key=True)
    AVname = Column(String(255), nullable=False, comment='审批流名称')
    # AVtype = Column(Integer, default=1, comment='审批流类型 1: 成为代理商审批 2:商品上架审批 3:订单退换货审批, 4: 提现审批 5: 用户资讯发布审批')
    AVstartid = Column(String(64), nullable=False, comment='发起人')
    AVlevel = Column(String(64), comment='当前审批人等级')
    AVstatus = Column(Integer, default=0, comment='审批状态 -20已取消 -10 拒绝 0 未审核 10审核通过')
    AVcontent = Column(String(64), comment='待审批的对象')
    PTid = Column(String(64), comment='审批流类型id')


# 权限
class Permission(Base):
    """审批流处理身份及层级"""
    __tablename__ = "Permission"
    PEid = Column(String(64), primary_key=True)
    # ADid = Column(String(64), nullable=False, comment='管理员id')
    # PEtype = Column(Integer, nullable=False, comment='审批流类型 1: 成为代理商审批 2:商品上架审批 3:订单退换货审批, 4: 提现审批 5: 用户资讯发布审批')
    PELevel = Column(Integer, nullable=False, comment='审批层级 1-10')
    PIid = Column(String(64), comment='权限id')
    PTid = Column(String(64), comment='审批流类型id')


class ApprovalNotes(Base):
    """审批流处理记录"""
    __tablename__= 'ApprovalNotes'
    ANid = Column(String(64), primary_key=True)
    AVid = Column(String(64), comment='审批流id')
    AVadname = Column(Text, comment='处理人姓名')
    ADid = Column(String(64), comment='处理人id')
    ANaction = Column(Integer, default=1, comment='审批意见 1 同意,0 提交 -1：拒绝')
    ANabo = Column(Text, comment='审批备注')


class PermissionItems(Base):
    """权限标签"""
    __tablename__ = 'PermissionItems'
    PIid = Column(String(64), primary_key=True)
    # PIType = Column(Integer, comment='权限标签')
    PIname = Column(Text, comment='权限名称')
    PIstatus = Column(Integer, default=1, comment='权限状态 1: 正常, -1: 被冻结')


class PermissionType(Base):
    """审批流类型"""
    __tablename__ = 'PermissionType'
    PTid = Column(String(64), primary_key=True)
    PTname = Column(Text, comment='审批流类型名称')
    PTmodelName = Column(Text, comment='类型关联表')


class PermissionNotes(Base):
    """审批流变更记录表"""
    __tablename__ = 'PermissionNotes'
    PNid = Column(String(64), primary_key=True)
    ADid = Column(String(64), comment='操作人id')
    PNcontent = Column(String(64), comment='被操作的权限')
    PINaction = Column(Text, comment='权限变更内容')
    PNType = Column(Integer, default=0, comment='权限变更类型 0 权限标签 1 审批流类型 2 审批流处理身份及层级')


class AdminPermission(Base):
    """管理员权限标签表"""
    __tablename__ = 'AdminPermission'
    ADPid = Column(String(64), primary_key=True)
    ADid = Column(String(64), comment='管理员id')
    PIid = Column(String(64), comment='标签id')
