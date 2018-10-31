# -*- coding: utf-8 -*-
from datetime import datetime

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

#
# class OrderMain(Base):
#     """
#     订单主单
#     """
#
# class OrderPart(Base):
#     """
#     订单副单
#     """
#
