# -*- coding:utf8 -*-
from datetime import datetime

from sqlalchemy.dialects.mysql import LONGTEXT
from sqlalchemy import Column, create_engine, Integer, String, Text, Float, Boolean, orm, DateTime
from config import dbconfig as cfg
from models.base_model import BaseModel, auto_createtime
import json


DB_PARAMS = "{0}://{1}:{2}@{3}/{4}?charset={5}".format(
    cfg.sqlenginename,
    cfg.username,
    cfg.password,
    cfg.host,
    cfg.database,
    cfg.charset)
mysql_engine = create_engine(DB_PARAMS, echo=False)


class Product(BaseModel):
    """
    商品
    """

class ProductSku(BaseModel):
    """
    商品SKU
    """

class Carts(BaseModel):
    """
    购物车
    """

class OrderMain(BaseModel):
    """
    订单主单
    """

class OrderPart(BaseModel):
    """
    订单副单
    """

class Users(BaseModel):
    """
    用户表
    """

class Items(BaseModel):
    """
    标签
    """

class ProductItems(BaseModel):
    """
    商品标签关联表
    """

class Reviews(BaseModel):
    """
    评论
    """

class ProductCategory(BaseModel):
    """
    商品类目
    """

class ProductBrand(BaseModel):
    """
    商品品牌
    """

class PlanetNews(BaseModel):
    """
    资讯
    """

class ShoppingAddress(BaseModel):
    """
    收货地址
    """

class Logistics(BaseModel):
    """
    物流
    """

class Card(BaseModel):
    """
    优惠券
    """

class CardPackage(BaseModel):
    """
    优惠券卡包
    """

class CoinList(BaseModel):
    """
    积分记录
    """

class SaleMessage(BaseModel):
    """
    商家推广信息
    """

class TrialCommodity(BaseModel):
    """
    试用商品
    """

class UserInvite(BaseModel):
    """
    用户邀请
    """