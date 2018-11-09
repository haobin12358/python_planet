# -*- coding: utf-8 -*-
from datetime import datetime

from sqlalchemy import Column, create_engine, Integer, String, Text, Float, Boolean, orm, DateTime, DECIMAL

from planet.common.base_model import Base


class User(Base):
    """
    用户表
    """
    __tablename__ = "User"
    USid = Column(String(64), primary_key=True)
    USname = Column(String(255), nullable=False, comment='用户名')
    USrealname = Column(String(255), comment='用户真实姓名')
    UStelphone = Column(String(13), nullable=False, comment='手机号')
    USgender = Column(Integer, default=0, comment='性别 {0: man, 1: woman')
    USbirthday = Column(DateTime, comment='出生日期')
    USidentification = Column(String(24), comment='身份证号')
    USheader = Column(Text, default='用户头像')
    USopenid1 = Column(Text, comment='公众号1 openid')
    USopenid2 = Column(Text, comment='公众号2 openid')
    USsupper1 = Column(String(64), comment='一级代理商id')  # 如果一级代理商为空，表示该用户为平台用户
    USsupper2 = Column(String(64), comment='二级代理商id')  # 如果二级代理商为空，则佣金抽成全归一级
    USCommission = Column(Float, comment='佣金分成')        # 总体佣金分成比例
    USintegral = Column(Integer, comment='积分')
    USlevel = Column(Integer, default=1, comment='等级 {1：普通游客，2：代理商}')
    USfrom = Column(Integer, default=1, comment='注册来源 {1: 微信h5, 2: app}')
    USqrcode = Column(Text, comment='用户二维码')

class UserLoginTime(Base):
    __tablename__ = 'UserLoginTime'
    ULTid = Column(String(64), primary_key=True)
    USid = Column(String(64), nullable=False, comment='用户id')
    # USTcreatetime = Column(DateTime, default=datetime.now(), comment='登录时间')
    USTip = Column(String(64), comment='登录ip地址')


class UserCommission(Base):
    __tablename__ = 'UserCommission'
    UCid = Column(String(64), primary_key=True)
    OMid = Column(String(64), comment='佣金来源订单')
    UCcommission = Column(DECIMAL, comment='获取佣金')
    USid = Column(String(64), comment='用户id')
    UCstatus = Column(Integer, default=0, comment='佣金状态{0：预期到账, 1: 已到账, 2: 已提现}')
    # UCcreateTime = Column(DateTime, default=datetime.now(), comment='佣金创建时间')


class IdentifyingCode(Base):
    """验证码"""
    __tablename__ = "identifyingcode"
    ICid = Column(String(64), primary_key=True)
    ICtelphone = Column(String(14), nullable=False)  # 获取验证码的手机号
    ICcode = Column(String(8), nullable=False)    # 获取到的验证码


class UserSearchHistory(Base):
    """用户搜索记录"""
    __tablename__ = 'UserSearchHistory'
    USHid = Column(String(64), primary_key=True)
    USid = Column(String(64), nullable=False, comment='用户id')
    USHname = Column(String(64), nullable=False, comment='搜索词')


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


class UserAddress(Base):
    """
    用户地址表
    """
    __tablename__ = 'UserAddress'
    UAid = Column(String(64), primary_key=True)
    USid = Column(String(64), comment='用户')
    UAname = Column(String(16), nullable=False, comment='收货人姓名')
    UAphone = Column(String(16), nullable=False, comment='收货人电话')
    UAtext = Column(String(255), nullable=False, comment='具体地址')
    UApostalcode = Column(String(8), comment='邮政编码')
    UAdefault = Column(Boolean, default=False, comment='默认收获地址')
    UAisdelete = Column(Boolean, default=False, comment='是否删除')
    areaid = Column(String(8), nullable=False, comment='关联的区域id')
