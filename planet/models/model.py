# -*- coding:utf8 -*-
from datetime import datetime

from sqlalchemy import Column, create_engine, Integer, String, Text, Float, Boolean, orm, DateTime

from planet.common.base_model import Base
from planet.config import secret as cfg


DB_PARAMS = "{0}://{1}:{2}@{3}/{4}?charset={5}".format(
    cfg.sqlenginename,
    cfg.username,
    cfg.password,
    cfg.host,
    cfg.database,
    cfg.charset)
mysql_engine = create_engine(DB_PARAMS, echo=False)


class Users(Base):
    """
    用户表
    """

class Reviews(Base):
    """
    评论
    """

class PlanetNews(Base):
    """
    资讯
    """

class ShoppingAddress(Base):
    """
    收货地址
    """

class Logistics(Base):
    """
    物流
    """

class Card(Base):
    """
    优惠券
    """

class CardPackage(Base):
    """
    优惠券卡包
    """

class CoinList(Base):
    """
    积分记录
    """

class SaleMessage(Base):
    """
    商家推广信息
    """

class TrialCommodity(Base):
    """
    试用商品
    """

class UserInvite(Base):
    """
    用户邀请
    """
