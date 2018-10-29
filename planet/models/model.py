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


# 疑问, 资讯的分类和商品的一级类目有关系吗
# ui购物车中的北面南面是什么意思
class Products(Base):
    """
    商品
    """
    __tablename__ = "Products"
    PRid = Column(String(64), primary_key=True)
    PRtitle = Column(String(255), nullable=False, comment='标题')
    PRprice = Column(Float, nullable=False, comment='价格')
    PRlinePrice = Column(Float, comment='划线价格')
    PRfreight = Column(Float, default=0, comment='运费')
    PRstocks = Column(Integer, comment='库存')
    PRstatus = Column(Integer, default=0, comment='状态  0 正常 10下架')
    PRmainpic = Column(String(255), comment='主图')
    PCid = Column(String(64), comment='分类id')
    PBid = Column(String(64), comment='品牌id')
    PRdesc = Column(Text, comment='商品详细介绍')
    PRremarks = Column(String(255), comment='备注')


class ProductSku(Base):
    """
    商品SKU
    """
    __tablename__ = 'ProductSku'
    SKUid = Column(String(64), primary_key=True)
    PRid = Column(String(64), nullable=False, comment='产品id')
    SKUpic = Column(String(255), nullable=False, comment='图片')
    SKUdetail = Column(Text, comment='sku属性信息')
    SKUprice = Column(Float, nullable=False, comment='价格')
    SKUstock = Column(Integer, comment='库存')


class ProductSkuValue(Base):
    """
    商品sku属性值
    """
    __tablename__ = 'ProductSkuValue'
    PSKUid = Column(String(64), primary_key=True)
    PRid = Column(String(64), nullable=False, comment='产品id')
    PSKUvalue = Column(Text, comment='商品属性值')


class ProductImage(Base):
    """
    商品图片
    """
    __tablename__ = 'ProductImage'
    PIid = Column(String(64), primary_key=True)
    PRid = Column(String(64), nullable=False, comment='商品id')
    PIpic = Column(String(255), nullable=False, comment='商品图片')


class ProductBrand(Base):
    """
    商品品牌
    """
    __tablename__ = 'ProductBrand'
    PBid = Column(String(64), primary_key=True)
    PBlogo = Column(String(255), comment='logo')
    PBname = Column(String(32), comment='名字')


class ProductScene(Base):
    """
    场景
    """
    __tablename__ = 'ProductScene'
    PSid = Column(String(64), primary_key=True)
    PSpic = Column(String(255), nullable=False, comment='图片')
    PSname = Column(String(16), nullable=False, comment='名字')
    PSsort = Column(Integer, comment='顺序标志')


class Items(Base):
    """
    标签, 标签是场景下的小标签
    """
    __tablename__ = 'ProductSceneItems'
    ITid = Column(String(64), primary_key=True)
    PSid = Column(String(64), nullable=False, comment='场景id')
    ITname = Column(String(16), nullable=False, comment='标签名字')
    ITsort = Column(Integer, comment='顺序')


class ProductItems(Base):
    """
    商品标签关联表
    """
    __tablename__ = 'ProductItems'
    PIid = Column(String(64), primary_key=True)
    PRid = Column(String(64), nullable=False, comment='商品id')
    ITid = Column(String(64), nullable=False, comment='标签id')


class ProductCategory(Base):
    """
    商品分类(共3级)
    """
    __tablename__ = 'ProductCategory'
    PCid = Column(String(64), primary_key=True)
    PCtype = Column(Integer, nullable=False, comment='类目级别, 1: 一级, 2: 二级, 3: 三级')
    PCdesc = Column(String(125), comment='类别描述')
    ParentPCid = Column(String(64), comment='父类别id, 为空则为一级主类别')
    PCsort = Column(String(64), comment='显示顺序')
    PCpic = Column(String(255), comment='图片')


class IndexProductBrand(Base):
    """
    首页显示的品牌
    """
    __tablename__ = 'IndexProductBrand'
    IPBid = Column(String(64), primary_key=True)
    PBid = Column(String(64), nullable=False, comment='商品品牌')
    IPBsort = Column(Integer, comment='顺序标志')


class IndexProductBrandItem(Base):
    """
    品牌推荐展示的商品
    """
    __tablename__ = 'IndexProductBrandItem'
    IPBIid = Column(String(64), primary_key=True)
    PRid = Column(String(64), primary_key=True, comment='商品')
    IPBIsort = Column(Integer, comment='顺序')


# class Carts(Base):
#     """
#     购物车
#     """
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
# class Users(Base):
#     """
#     用户表
#     """
#
# class Reviews(Base):
#     """
#     评论
#     """
#
# class PlanetNews(Base):
#     """
#     资讯
#     """
#
# class ShoppingAddress(Base):
#     """
#     收货地址
#     """
#
# class Logistics(Base):
#     """
#     物流
#     """
#
# class Card(Base):
#     """
#     优惠券
#     """
#
# class CardPackage(Base):
#     """
#     优惠券卡包
#     """
#
# class CoinList(Base):
#     """
#     积分记录
#     """
#
# class SaleMessage(Base):
#     """
#     商家推广信息
#     """
#
# class TrialCommodity(Base):
#     """
#     试用商品
#     """
#
# class UserInvite(Base):
#     """
#     用户邀请
#     """