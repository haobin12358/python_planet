# -*- coding: utf-8 -*-
from sqlalchemy import create_engine, Integer, String, Text, Float, Boolean, orm, DateTime

from planet.common.base_model import Base, Column


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
    PRsalesValue = Column(Integer, default=0, comment='销量')
    PRstatus = Column(Integer, default=0, comment='状态  0 正常, 10 审核中 60下架')
    PRmainpic = Column(String(255), comment='主图', url=True)
    PRattribute = Column(Text, comment='商品属性 ["网络","颜色","存储"]')
    PCid = Column(String(64), comment='分类id')
    PBid = Column(String(64), comment='品牌id')
    PRdesc = Column(Text, comment='商品详细介绍', url_list=True)
    PRremarks = Column(String(255), comment='备注')
    PRfrom = Column(Integer, default=0, comment='商品来源 0 平台发布 10 店主发布')
    PRdescription = Column(Text, comment='商品描述')
    CreaterId = Column(String(64), nullable=False, comment='创建者')
    PRaverageScore = Column(Float(precision=10, scale=2), default=10.00, comment='商品评价平均分')
    # PRcode = Column(String(64), comment='商品的外部编号')

    @orm.reconstructor
    def __init__(self):
        super(Products, self).__init__()
        self.add('createtime')


class ProductMonthSaleValue(Base):
    """商品月销量"""
    __tablename__ = 'ProductMonthSaleValue'
    PMSVid = Column(String(64), primary_key=True)
    PRid = Column(String(64), nullable=False, comment='商品id')
    PMSVnum = Column(Integer, default=0)


class ProductSku(Base):
    """
    商品SKU
    """
    __tablename__ = 'ProductSku'
    SKUid = Column(String(64), primary_key=True)
    PRid = Column(String(64), nullable=False, comment='产品id')
    SKUpic = Column(String(255), nullable=False, comment='图片', url=True)
    SKUattriteDetail = Column(Text, comment='sku属性信息 ["电信","白","16G"]')
    SKUprice = Column(Float, nullable=False, comment='价格')
    SKUstock = Column(Integer, comment='库存')
    SKUsn = Column(String(64), default=SKUid, nullable=False, comment='sku编码')


class ProductSkuValue(Base):
    """
    商品sku属性顺序汇总
    """
    __tablename__ = 'ProductSkuValue'
    PSKUid = Column(String(64), primary_key=True)
    PRid = Column(String(64), nullable=False, comment='商品id')
    PSKUvalue = Column(Text, comment='属性名[[联通, 电信], [白, 黑], [16G, 32G]]')


class ProductImage(Base):
    """
    商品图片
    """
    __tablename__ = 'ProductImage'
    PIid = Column(String(64), primary_key=True)
    PRid = Column(String(64), nullable=False, comment='商品id')
    PIpic = Column(String(255), nullable=False, comment='商品图片', url=True)
    PIsort = Column(Integer, comment='顺序')


class ProductBrand(Base):
    """
    商品品牌
    """
    __tablename__ = 'ProductBrand'
    PBid = Column(String(64), primary_key=True)
    PBlogo = Column(String(255), comment='logo', url=True)
    PBname = Column(String(32), comment='名字')
    PBdesc = Column(String(255), comment='简介')
    PBlinks = Column(String(255), comment='官网, 待用')
    PBbackgroud = Column(String(255), comment='背景图', url=True)
    PBstatus = Column(Integer, default=0, comment='状态 0正常, 10下架')


class BrandWithItems(Base):
    """品牌-标签关联表"""
    __tablename__ = 'BrandwithItems'
    BWIid = Column(String(64), primary_key=True)
    ITid = Column(String(64), nullable=False, comment='标签id')
    PBid = Column(String(64), nullable=False, comment='品牌标签id')


class ProductScene(Base):
    """
    场景
    """
    __tablename__ = 'ProductScene'
    PSid = Column(String(64), primary_key=True)
    PSpic = Column(String(255), nullable=False, comment='图片', url=True)
    PSname = Column(String(16), nullable=False, comment='名字')
    PSsort = Column(Integer, comment='顺序标志')


class SceneItem(Base):
    """
    场景-标签
    """
    __tablename__ = 'SceneItem'
    SIid = Column(String(64), primary_key=True)
    PSid = Column(String(64), nullable=False, comment='场景id')
    ITid = Column(String(64), nullable=False, comment='标签id')


class Items(Base):
    """
    商品, 资讯, 优惠券,品牌标签
    """
    __tablename__ = 'Items'
    ITid = Column(String(64), primary_key=True)
    ITname = Column(String(16), nullable=False, comment='标签名字')
    ITsort = Column(Integer, comment='顺序')
    ITdesc = Column(String(255), comment='标签描述')
    ITtype = Column(Integer, index=True, default=0, comment='标签类型 {0: 商品, 10:资讯, 20:优惠券, 40: 品牌}')
    ITrecommend = Column(Boolean, default=False, comment='是否推荐(圈子)')
    ITauthority = Column(Integer, default=0, comment='标签权限  0 无限制 10新人可查看 20 管理员可看, 30 其他特殊')
    ITposition = Column(Integer, default=0, comment='位置信息 0 场景推荐页, 10 首页 20 新人页, 30 其他特殊')


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
    PCname = Column(String(16), nullable=False, comment='类别名')
    PCdesc = Column(String(125), comment='类别描述')
    ParentPCid = Column(String(64), comment='父类别id, 为空则为一级主类别')
    PCsort = Column(String(64), comment='显示顺序')
    PCpic = Column(String(255), comment='图片', url=True)
    PCtopPic = Column(String(255), url=True, comment='一级分类顶部图')


class Supplizer(Base):
    """供应商"""
    __tablename__ = 'Supplizer'
    SUid = Column(String(64), primary_key=True)
    SUloginPhone = Column(String(11), nullable=False, index=True, unique=True, comment='登录手机号')
    SUlinkPhone = Column(String(11), default=SUloginPhone, comment='供应商联系电话')
    SUname = Column(String(16), default=SUlinkPhone, comment='供应商名字')
    SUlinkman = Column(String(16), nullable=False, comment='供应商联系人')
    SUaddress = Column(String(255), nullable=False, comment='供应商地址')
    SUstatus = Column(Integer, default=0, comment='状态, 0 正常 10 禁用')
    SUisseller = Column(Boolean, default=False, comment='是否是卖家')  # 未知用处
    SUbanksn = Column(String(32), comment='卡号')
    SUbankname = Column(String(64), comment='银行')
    SUpassword = Column(String(255), comment='供应商密码密文')
    SUheader = Column(String(255), comment='头像', url=True)
    SUcontract = Column(Text, url_list=True, comment='合同列表')
    # 其他


class SupplizerProduct(Base):
    """供应商商品表"""
    __tablename__ = 'SupplizerProduct'
    SPid = Column(String(64), primary_key=True)
    PRid = Column(String(64), nullable=False, index=True, comment='商品id')
    SUid = Column(String(64), nullable=False, comment='供应商id')


# class SupplizerBrand(Base):
#     """供应商品牌表"""
#     SUBid = Column(String(64), primary_key=True)
#     PBid = Column(String(64), nullable=False, comment='品牌id')
#     SUid = Column(String(64), nullable=False, comment='供应商id')

# class WareHouse(Base):
#     """仓库"""
#     __tablename__ = 'WareHouse'
#     WAid = Column(String(64), primary_key=True)
#     WAname = Column(String(32), nullable=False, comment='仓库名字')
#     WAphone = Column(String(11), nullable=False, comment='仓库电话')
#     WAcontact = Column(String(16), nullable=False, comment='仓库联系人')
#     WAaddress = Column(String(64), nullable=False, comment='地址')
#     WAstatus = Column(Integer, default=0, comment='状态, 待用')
#
#
# class WareHouseProduct(Base):
#     """仓库库存表"""
#     __tablename__ = 'WareHouseProduct'
#     WHPid = Column(String(64), primary_key=True)
#     PRid = Column(String(64), nullable=False, comment='商品id')
#     WAid = Column(String(64), nullable=False, comment='仓库id')
#     PRnum = Column(Integer, default=0, comment='当前商品数量')
#
#
# class WareHouseInFlow(Base):
#     """入库"""
#     __tablename__ = 'WareHouseInFlow'
#     WHIFid = Column(String(64), primary_key=True)
#     PRid = Column(String(64), nullable=False, comment='商品id')
#     SUid = Column(String(64), nullable=False, comment='供应商id')
#     PRnum = Column(Integer, nullable=False, comment='数量')
#     # sku?
