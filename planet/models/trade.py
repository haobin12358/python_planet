# -*- coding: utf-8 -*-
from sqlalchemy import Integer, String, Text, Float, DateTime, Boolean

from planet.common.base_model import Base, Column


class Carts(Base):
    """
    购物车
    """
    __tablename__ = 'Carts'
    CAid = Column(String(64), primary_key=True)
    USid = Column(String(64), nullable=False, comment='用户id')
    SKUid = Column(String(64), nullable=False, comment='商品sku')
    CAnums = Column(Integer, default=1, comment='数量')
    PBid = Column(String(64), comment='品牌id')
    PRid = Column(String(64), comment='商品id')


class OrderMain(Base):
    """
    订单主单, 下单时每种品牌单独一个订单, 但是一并付费
    """
    __tablename__ = 'OrderMain'
    OMid = Column(String(64), primary_key=True)
    OMno = Column(String(64), nullable=False, comment='订单编号')
    OPayno = Column(String(64), comment='付款流水号,与orderpay对应')
    USid = Column(String(64), nullable=False, comment='用户id')
    UseCoupon = Column(Boolean, default=False, comment='是否优惠券')
    OMfrom = Column(Integer, default=0, comment='来源: 0: 购物车, 10: 商品详情 20: 店主权限')
    PBname = Column(String(32), nullable=False, comment='品牌名')
    PBid = Column(String(64), nullable=False, comment='品牌id')
    OMclient = Column(Integer, default=0, comment='下单设备: 0: 微信, 10: app')
    OMfreight = Column(Float, default=0, comment='运费')
    OMmount = Column(Float, nullable=False, comment='总价')
    OMtrueMount = Column(Float, nullable=False, comment='实际总价')
    OMstatus = Column(Integer, default=0, comment='订单状态 0待付款,10待发货,20待收货,30完成,-40取消交易')
    OMinRefund = Column(Boolean, default=False, comment='有商品在售后状态')
    OMmessage = Column(String(255), comment='留言')
    # 收货信息
    OMrecvPhone = Column(String(11), nullable=False, comment='收货电话')
    OMrecvName = Column(String(11), nullable=False, comment='收货人姓名')
    OMrecvAddress = Column(String(255), nullable=False, comment='地址')
    # # 卖家信息 todo
    # PRfrom = Column(Integer, default=0, comment='商品来源 0 平台发布 10 店主发布')
    # CreaterId = Column(String(64), nullable=False, comment='商品发布者')
    # # 上级信息
    # UPperid = Column(String(64), comment='上级id')
    # UPperid2 = Column(String(64), comment='上上级id')


class OrderPay(Base):
    """
    付款流水
    """
    __tablename__ = 'OrderPay'
    OPayid = Column(String(64), primary_key=True)
    OPayno = Column(String(64), index=True,comment='交易号, 自己生成')
    OPayType = Column(Integer, default=0, comment='支付方式 0 微信 10 支付宝')
    OPaytime = Column(DateTime, comment='付款时间')
    OPayMount = Column(Integer, comment='付款金额')
    OPaysn = Column(String(64), comment='第三方支付流水')
    OPayJson = Column(Text, comment='回调原文')
    OPaymarks = Column(String(255), comment='备注')


class OrderCoupon(Base):
    __tablename__ = 'OrderRaward'
    OCid = Column(String(64), primary_key=True)
    CPid = Column(String(64), nullable=False, comment='优惠券')
    OCnum = Column(Integer, default=1, comment='使用数量')
    OCreduce = Column(Float, nullable=False, comment='减额')
    # 其他


class OrderPart(Base):
    """
    订单副单
    """
    __tablename__ = 'OrderPart'
    OPid = Column(String(64), primary_key=True)
    OMid = Column(String(64), nullable=False, comment='订单id')
    SKUid = Column(String(64), nullable=False, comment='skuid')
    PRid = Column(String(64),  nullable=False, comment='商品id')
    PRattribute = Column(Text, comment='商品属性 ["网络","颜色","存储"]')
    SKUattriteDetail = Column(Text, nullable=False, comment='sku详情[]')
    SKUprice = Column(Float, nullable=False, comment='单价')
    PRtitle = Column(String(255), nullable=False, comment='商品标题')
    PRmainpic = Column(String(255), nullable=False, comment='主图', url=True)
    OPnum = Column(Integer, default=1, comment='数量')
    OPsubTotal = Column(Float, default=SKUprice, comment='价格小计')
    OPisinORA = Column(Boolean, default=False, comment='是否在售后')


class OrderRefundApply(Base):
    """订单售后申请"""
    __tablename__ = 'OrderRefundApply'
    ORAid = Column(String(64), primary_key=True)
    ORAsn = Column(String(64), nullable=False, comment='售后申请编号')
    OMid = Column(String(64), nullable=False, comment='主单id')
    OPid = Column(String(64), nullable=False, comment='副单id')
    USid = Column(String(64), nullable=False, comment='用户id')
    ORAstate = Column(Integer, default=0, comment='类型: 0 退货退款 10 暂定')
    ORAreason = Column(String(255), nullable=False, comment='退款原因')
    ORAmount = Column(Float, nullable=False, comment='退款金额')
    ORAaddtion = Column(String(255), comment='退款说明')
    ORaddtionVoucher = Column(Text, comment='退款说明图片')
    ORAproductStatus = Column(Integer, default=0, comment='0已收货, 1 未收货')
    ORAstatus = Column(Integer, default=0, comment='状态-20已取消 -10 拒绝 0 未审核 10审核通过')
    ORAcheckReason = Column(String(255), comment='审核原因')
    ORAcheckTime = Column(DateTime, comment='审核时间')
    ORAnote = Column(String(255), comment='备注')


class OrderRefund(Base):
    """订单售后表"""
    __tablename__ = 'OrderRefund'
    ORid = Column(String(64), primary_key=True)
    OMid = Column(String(64), nullable=False, comment='订单id')
    OPid = Column(String(64), nullable=False, comment='附单id')
    # 其他


class OrderLogistics(Base):
    """订单物流"""
    __tablename__ = 'OrderLogistics'
    OLid = Column(String(64), primary_key=True)
    OMid = Column(String(64), nullable=False, comment='主单id')
    # OPid = Column(String(125), comment='副单物流')
    OLcompany = Column(String(32), nullable=False, comment='物流公司')
    OLexpressNo = Column(String(64), nullable=False, comment='物流单号')
    OLsearchStatus = Column(String(8), default=0, comment='物流查询状态 polling:监控中，shutdown:结束，abort:中止，updateall：重新推送。')
    OLsignStatus = Column(Integer, default=-1, comment='签收状态 -3 等待揽收 0在途中、1已揽收、2疑难、3已签收')
    OLdata = Column(Text, comment='查询结果')
    OLlastresult = Column(String(255), comment='物流最后状态')


class LogisticsCompnay(Base):
    """快递公司"""
    __tablename__ = 'LogisticsCompnay'
    id = Column(Integer, autoincrement=True, primary_key=True)
    LCname = Column(String(64), nullable=False, index=True, comment='公司名称')
    LCcode = Column(String(64), nullable=False, index=True, comment='快递公司编码')
