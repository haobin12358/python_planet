# -*- coding: utf-8 -*-
from datetime import datetime
from decimal import Decimal

from sqlalchemy import Column, create_engine, Integer, String, Text, Float, Boolean, orm, DateTime

from planet.common.base_model import Base


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
    订单主单
    """
    __tablename__ = 'OrderMain'
    OMid = Column(String(64), primary_key=True)
    OMno = Column(String(64), nullable=False, comment='订单编号')
    OMsn = Column(String(64), comment='交易号')  # 调起支付时使用, 多订单同时支付使用相同值
    USid = Column(String(64), nullable=False, comment='用户id')
    OMfrom = Column(Integer, default=0, comment='来源: 0: 购物车, 10: 商品详情')
    PBname = Column(String(32), nullable=False, comment='品牌名')
    PBid = Column(String(64), nullable=False, comment='品牌id')
    OMclient = Column(Integer, default=0, comment='下单设备: 0: 微信, 10: app')
    OMpayType = Column(Integer, default=0, comment='支付方式')
    OMpaytime = Column(DateTime, comment='付款时间')
    OMfreight = Column(String, default=0, comment='运费')
    OMmount = Column(Float, nullable=False, comment='总价')
    OMtrueMount = Column(Float, nullable=False, comment='实际总价')
    OMpayTradeNo = Column(String(255), comment='第三方支付流水')
    OMstatus = Column(Integer, default=0, comment='订单状态 0未付款,10已付款,20已发货,30已签收')


class OrderPart(Base):
    """
    订单副单
    """
    __tablename__ = 'OrderPart'
    OPid = Column(String(64), primary_key=True)
    OMid = Column(String(64), nullable=False, comment='订单id')
    SKUid = Column(String(64), nullable=False, comment='skuid')
    SKUdetail = Column(Text, nullable=False, comment='sku详情')
    SKUprice = Column(Float, nullable=False, comment='单价')
    PRtitle = Column(String(255), nullable=False, comment='商品标题')
    PRmainpic = Column(String(255), nullable=False, comment='主图')
    OPnum = Column(Integer, default=1, comment='数量')
    OPsubTotal = Column(Float, default=SKUprice, comment='价格小计')
    OPstatus = Column(Integer, default=0, comment='状态: 0正常状态, -10退货申请,-20退货中,-30已退货,-40取消交易')
