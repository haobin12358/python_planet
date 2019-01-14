# -*- coding: utf-8 -*-
import datetime
from sqlalchemy import Integer, String, Text, Float, Boolean, DateTime, DECIMAL

from planet.common.base_model import Base, Column


class User(Base):
    """
    用户表
    """
    __tablename__ = "User"
    USid = Column(String(64), primary_key=True)
    USname = Column(String(255), nullable=False, comment='用户名')
    USrealname = Column(String(255), comment='用户真实姓名')
    UStelphone = Column(String(13), comment='手机号')
    USgender = Column(Integer, default=0, comment='性别 {0: man, 1: woman')
    USbirthday = Column(DateTime, comment='出生日期')
    USidentification = Column(String(24), comment='身份证号')
    USheader = Column(Text, default='用户头像', url=True)
    USopenid1 = Column(Text, comment='服务号 openid')
    USopenid2 = Column(Text, comment='公众号2 openid')
    USsupper1 = Column(String(64), comment='一级代理商id')
    USsupper2 = Column(String(64), comment='二级代理商id')
    USsupper3 = Column(String(64), comment='三级代理商id')
    USCommission1 = Column(DECIMAL(scale=2), comment='当用户作为一级时, 佣金分成')       # 一级佣金分成比例
    USCommission2 = Column(DECIMAL(scale=2), comment='佣金分成')       # 二级佣金分成比例
    USCommission3 = Column(DECIMAL(scale=2), comment='佣金分成')       # 三级佣金分成比例
    USintegral = Column(Integer, comment='积分')
    CommisionLevel = Column(Integer, default=1)
    USlevel = Column(Integer, default=1, comment='等级 {1：普通游客，2：代理商, 3: 申请成代理商中}')
    USfrom = Column(Integer, default=1, comment='注册来源 {1: 微信h5, 2: app}')
    USqrcode = Column(Text, url=True, comment='用户二维码')
    USpaycode = Column(Text, comment='支付密码')
    UScontinuous = Column(Integer, default=0, comment='连续签到天数')
    UStoAgentTime = Column(DateTime, comment='成为代理商时间')


class UserLoginTime(Base):
    __tablename__ = 'UserLoginTime'
    ULTid = Column(String(64), primary_key=True)
    USid = Column(String(64), nullable=False, comment='用户id')
    # USTcreatetime = Column(DateTime, default=datetime.now(), comment='登录时间')
    USTip = Column(String(64), comment='登录ip地址')
    ULtype = Column(Integer, default=1, comment='登录用户类型 1: 用户，2 管理员')


class UserCommission(Base):
    """用户佣金"""
    __tablename__ = 'UserCommission'
    UCid = Column(String(64), primary_key=True)
    UCcommission = Column(DECIMAL(precision=28, scale=2), comment='获取佣金')
    USid = Column(String(64), comment='用户或供应商id 0表示平台')
    CommisionFor = Column(Integer, default=20, comment='0 平台, 10 供应商, 20 普通用户')
    FromUsid = Column(String(64), comment='订单来源用户')
    UCstatus = Column(Integer, default=0, comment='佣金状态{-1: 异常, 0：预期到账, 1: 已到账, 2: 已提现}')
    UCtype = Column(Integer, default=0, comment='收益类型 0：佣金 1：新人商品 2：押金')
    UCendTime = Column(DateTime, comment='预期到账时间')
    PRtitle = Column(String(255), comment='商品标题')
    SKUpic = Column(Text, url=True, comment='商品sku主图')
    OMid = Column(String(64), comment='佣金来源订单')
    OPid = Column(String(64), comment='分单id')


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
    USHtype = Column(Integer, default=0, comment='搜索类型0 商品, 10 圈子')


class Admin(Base):
    """
    管理员
    """
    __tablename__ = 'Admin'
    ADid = Column(String(64), primary_key=True)
    ADnum = Column(Integer, autoincrement=True)
    ADname = Column(String(255), comment='管理员名')
    ADtelphone = Column(String(13), comment='管理员联系电话')
    ADpassword = Column(Text, nullable=False, comment='密码')
    ADfirstpwd = Column(Text, comment=' 初始密码 明文保存')
    ADfirstname = Column(Text, comment=' 初始用户名')
    ADheader = Column(Text, comment='头像', url=True)
    ADlevel = Column(Integer, default=2, comment='管理员等级，{1: 超级管理员, 2: 普通管理员 3: 代理商}')
    ADstatus = Column(Integer, default=0, comment='账号状态，{0:正常, 1: 被冻结, 2: 已删除}')
    # ADcreateTime = Column(DateTime, default=datetime.now(), comment='创建时间')


class AdminNotes(Base):
    """
    管理员变更记录
    """
    __tablename__ = 'AdminNotes'
    ANid = Column(String(64), primary_key=True)
    ADid = Column(String(64), nullable=False, comment='管理员id')
    ANaction = Column(Text, comment='变更动作')
    # ANcreateTime = Column(DateTime, default=datetime.now(), comment='变更时间')
    ANdoneid = Column(String(64), comment='修改人id')


class UserAddress(Base):
    """
    用户地址表
    """
    __tablename__ = 'UserAddress'
    UAid = Column(String(64), primary_key=True)
    USid = Column(String(64), comment='用户id/供应商id')
    UAname = Column(String(16), nullable=False, comment='收货人姓名')
    UAphone = Column(String(16), nullable=False, comment='收货人电话')
    UAtext = Column(String(255), nullable=False, comment='具体地址')
    UApostalcode = Column(String(8), comment='邮政编码')
    UAdefault = Column(Boolean, default=False, comment='默认收获地址')
    AAid = Column(String(8), nullable=False, comment='关联的区域id')
    UAFrom = Column(Integer, default=0, comment='地址所属 0:用户 10:供应商')


class UserMedia(Base):
    """
    用户身份证图片表
    """
    __tablename__ = 'UserMetia'
    UMid = Column(String(64), primary_key=True)
    USid = Column(String(64), comment='用户id')
    UMurl = Column(Text, url=True, comment='图片路径')
    UMtype = Column(Integer, default=1, comment='图片类型 1: 身份证正面, 2: 身份证反面')


class IDCheck(Base):
    """实名认证查询"""
    __tablename__ = 'IDcheck'
    IDCid = Column(String(64), primary_key=True)
    IDCcode = Column(String(24), nullable=False, comment='查询所用的身份证')
    IDCname = Column(Text, comment='查询所用的姓名')
    IDCresult = Column(Boolean, default=False, comment='查询结果')
    IDCrealName = Column(Text, comment='查询结果里的真实姓名')
    IDCcardNo = Column(Text, comment='查询结果的真实身份证')
    IDCaddrCode = Column(Text, comment='查询结果的地区编码')
    IDCbirth = Column(Text, comment='生日')
    IDCsex = Column(Integer, comment='性别')
    IDCcheckBit = Column(String(2), comment='身份证最后一位')
    IDCaddr = Column(Text, comment='查询结果的地址信息，精确到县')
    IDCerrorCode = Column(String(8), comment='查询结果code')
    IDCreason = Column(Text, comment='查询结果')


class UserIntegral (Base):
    """用户积分表  ps 表名与类名不同"""
    __tablename__ = 'UserSignIn'
    UIid = Column(String(64), primary_key=True)
    USid = Column(String(64), comment='用户id')
    UIintegral = Column(Integer, comment='该动作产生的积分变化数')
    UIaction = Column(Integer, default=1, comment='积分变动原因 1 签到 2 积分商城消费')
    UItype = Column(Integer, default=1, comment='积分变动类型 1 收入 2 支出')


class AddressProvince(Base):
    """省"""
    __tablename__ = 'AddressProvince'
    APid = Column(String(8), primary_key=True, comment='省id')
    APname = Column(String(20), nullable=False, comment='省名')


class AddressCity(Base):
    """市"""
    __tablename__ = 'AddressCity'
    ACid = Column(String(8), primary_key=True, comment='市id')
    ACname = Column(String(20), nullable=False, comment='市名')
    APid = Column(String(8), nullable=False, comment='省id')


class AddressArea(Base):
    """区县"""
    __tablename__ = 'AddressArea'
    AAid = Column(String(8), primary_key=True, comment='区县id')
    AAname = Column(String(32), nullable=False, comment='区县名')
    ACid = Column(String(8), nullable=False, comment='市名')


class UserSalesVolume(Base):
    """用户销售额 按月统计，需要总额需要累加 只累加自己的订单销售额"""
    __tablename__ = 'UserSalesvolume'
    USVid = Column(String(64), primary_key=True)
    USid = Column(String(64), comment='用户id')
    USVamount = Column(DECIMAL(precision=28, scale=2), comment='月度总额')
    USVamountagent = Column(DECIMAL(precision=28, scale=2), comment='月度代理商直销总额')


class UserInvitation(Base):
    """用户邀请记录表"""
    __tablename__ = 'UserInvitation'
    UINid = Column(String(64), primary_key=True)
    USInviter = Column(String(64), comment='邀请人')
    USInvited = Column(String(64), comment='被邀请人')


class UserWallet(Base):
    """用户钱包"""
    __tablename__ = 'UserWallet'
    UWid = Column(String(64), primary_key=True)
    USid = Column(String(64), comment='用户id')
    CommisionFor = Column(Integer, default=20, comment='0 平台, 10 供应商, 20 普通用户')
    UWbalance = Column(DECIMAL(precision=28, scale=2), comment='用户账户余额')
    UWtotal = Column(DECIMAL(precision=28, scale=2), comment='用户账户总额')
    UWcash = Column(DECIMAL(precision=28, scale=2), comment='用户账号可提现余额')
    UWexpect = Column(DECIMAL(precision=28, scale=2), comment='用户账号预期到账金额')


class CashNotes(Base):
    """用户提现记录"""
    __tablename__ = 'CashNotes'
    CNid = Column(String(64), primary_key=True)
    USid = Column(String(64), comment='用户id')
    CommisionFor = Column(Integer, default=20, comment='0 平台, 10 供应商, 20 普通用户')
    CNbankName = Column(Text, comment='开户行')
    CNbankDetail = Column(Text, comment='开户网点详情')
    CNcardNo = Column(String(32), comment='卡号')
    CNcashNum = Column(DECIMAL(precision=28, scale=2), comment='提现金额')
    CNcardName = Column(String(32), comment='开户人')
    CNstatus = Column(Integer, default=0, comment='提现状态 0: 审核中, 1: 审核通过, -1:拒绝')
    CNrejectReason = Column(Text, comment='拒绝理由')

