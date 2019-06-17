# -*- coding: utf-8 -*-
from datetime import date

from sqlalchemy import Integer, String, Date, Float, Text, DateTime, Boolean, DECIMAL, BIGINT
from sqlalchemy.dialects.mysql import LONGTEXT

from planet.common.base_model import Base, Column


class Activity(Base):
    """活动列表控制"""
    __tablename__ = 'Activity'
    ACid = Column(Integer, primary_key=True)
    ACbackGround = Column(String(255), nullable=False, url=True, comment='列表页背景图')
    ACtopPic = Column(String(255), nullable=False, url=True, comment='顶部图 ')
    ACbutton = Column(String(16), default='立即参与', comment='按钮文字')
    ACtype = Column(Integer, default=0, unique=True, index=True, comment='类型 0: 新人 1 猜数字 2 魔术礼盒 3 免费试用 4 限时活动 5 拼团竞猜')
    ACshow = Column(Boolean, default=True, comment='是否开放')
    ACdesc = Column(Text, comment='活动描述')
    ACname = Column(String(16), nullable=False, comment='名字')
    ACsort = Column(Integer, comment='顺序标志')


class ActivityDeposit(Base):
    __tablename__ = 'ActivityDeposit'
    """活动押金"""
    ACDid = Column(String(64), primary_key=True)
    USid = Column(String(64), nullable=False, comment='用户')
    ACtype = Column(Integer, default=2, comment='活动类型 {0,1,2,3,4,5}')
    ACDdeposit = Column(DECIMAL(precision=28, scale=2), nullable=False, comment='押金金额')
    ACDcontentId = Column(String(64), nullable=False, comment='具体活动的id, 如魔盒商品id')
    ACDstatus = Column(Integer, default=-20, comment='押金的状态, -20：无效 -10:已退还 0:已支付 10：已扣除')
    SKUid = Column(String(64), comment='购买的具体活动商品skuid')
    OPayno = Column(String(64), nullable=False, comment='支付流水号')


class TrialCommodity(Base):
    """试用商品"""
    __tablename__ = 'TrialCommodity'
    TCid = Column(String(64), primary_key=True)
    TCtitle = Column(String(255), nullable=False, comment='标题')
    TCdescription = Column(Text, comment='商品描述')
    TCdeposit = Column(DECIMAL(precision=28, scale=2), nullable=False, comment='押金')
    TCdeadline = Column(Integer, nullable=False, default=31, comment='押金期限{单位:天}')
    TCfreight = Column(Float, default=0, comment='运费')
    TCfrom = Column(Integer, comment='申请来源')
    TCstocks = Column(BIGINT, comment='库存')
    TCsalesValue = Column(BIGINT, default=0, comment='销量')
    TCstatus = Column(Integer, default=0, comment='状态  0 正常, 10 下架, 20 审核中')
    TCmainpic = Column(String(255), comment='主图', url=True)
    TCattribute = Column(Text, comment='商品属性 ["网络","颜色","存储"]')
    TCdesc = Column(LONGTEXT, comment='商品详细介绍', url_list=True)
    TCremarks = Column(String(255), comment='备注')
    CreaterId = Column(String(64), nullable=False, comment='创建者')
    PBid = Column(String(64), comment='品牌id')
    ApplyStartTime = Column(Date, nullable=False, comment='申请开始时间')
    ApplyEndTime = Column(Date, nullable=False, comment='申请结束时间')
    AgreeStartTime = Column(Date, default=ApplyStartTime, comment='最终确认起始时间')  # 同意之后不可为空
    AgreeEndTime = Column(Date, default=ApplyEndTime, comment='最终确认结束时间')
    TCrejectReason = Column(Text, comment='拒绝理由')


class TrialCommodityImage(Base):
    """试用商品图片"""
    __tablename__ = 'TrialCommodityImage'
    TCIid = Column(String(64), primary_key=True)
    TCid = Column(String(64), nullable=False, comment='试用商品id')
    TCIpic = Column(String(255), nullable=False, comment='商品图片', url=True)
    TCIsort = Column(Integer, comment='顺序')


class TrialCommoditySku(Base):
    """试用商品SKU"""
    __tablename__ = 'TrialCommoditySku'
    SKUid = Column(String(64), primary_key=True)
    TCid = Column(String(64), nullable=False, comment='试用商品id')
    SKUpic = Column(String(255), nullable=False, comment='图片', url=True)
    SKUattriteDetail = Column(Text, comment='sku属性信息 ["电信","白","16G"]')
    SKUprice = Column(DECIMAL(precision=28, scale=2), nullable=False, comment='价格')
    SKUstock = Column(BIGINT, comment='库存')


class TrialCommoditySkuValue(Base):
    """商品分类sku属性名"""
    __tablename__ = 'TrialCommoditySkuValue'
    TSKUid = Column(String(64), primary_key=True)
    TCid = Column(String(64), nullable=False, comment='试用商品id')
    TSKUvalue = Column(Text, comment='属性名["网络","颜色","存储"]')


class GuessNum(Base):
    """猜数字 参与记录"""
    __tablename__ = 'GuessNum'
    GNid = Column(String(64), primary_key=True)
    GNnum = Column(String(16), nullable=False, comment='猜测的数字')
    GNNAid = Column(String(64), comment='对应的申请单id')
    USid = Column(String(64), nullable=False, comment='用户id')
    GNdate = Column(Date, default=date.today, comment='参与的日期')
    SKUid = Column(String(64), comment='选购的商品')
    PRid = Column(String(64), comment='当日奖品')
    Price = Column(Float, comment='当日价格')


class CorrectNum(Base):
    """正确数字"""
    __tablename__ = 'CorrectNum'
    CNid = Column(String(64), primary_key=True)
    CNnum = Column(String(16), nullable=False, comment='正确的数字')
    CNdate = Column(Date, nullable=False, comment='日期')
    CNtype = Column(Integer, default=0, comment='结果类型 {0: 上证指数 1: 福彩3D}')
    CNissue = Column(String(10), comment='福彩期数')


class GuessAwardFlow(Base):
    """猜数字中奖和领奖记录"""
    __tablename__ = 'GuessAwardFlow'
    GAFid = Column(String(64), primary_key=True)
    GNid = Column(String(64), nullable=False, unique=True, comment='个人参与记录')
    GAFstatus = Column(Integer, default=0, comment='领奖状态 0 待领奖, 10 已领取 20 过期')
    OMid = Column(String(64), default='0')


class GuessNumAwardApply(Base):
    """申请参与猜数字"""
    __tablename__ = 'GuessNumAward'
    GNAAid = Column(String(64), primary_key=True)
    # GNAPid = Column(String(64), comment='申请商品id')
    SUid = Column(String(64), comment='发布者id')
    GNAAstarttime = Column(Date, nullable=False, comment='申请参与的起始时间')
    GNAAendtime = Column(Date, nullable=False, comment='申请参与的结束时间')
    GNAAfrom = Column(Integer, comment='申请来源, 0:供应商, 1: 平台管理员')
    GNAAstatus = Column(Integer, default=0, comment='申请状态, 0: 未处理, -10: 拒绝, 10: 通过')
    ADid = Column(String(64), comment='处理人')
    GNAArejectReason = Column(String(64), comment='拒绝理由')
    AgreeStartime = Column(Date, default=GNAAstarttime, comment='最终确认起始时间')  # 同意之后不可为空
    AgreeEndtime = Column(Date, default=GNAAendtime, comment='最终确认结束时间')


class GuessNumAwardProduct(Base):
    """猜数字商品表"""
    __tablename__ = 'GuessNumAwardProduct'
    GNAPid = Column(String(64), primary_key=True)
    GNAAid = Column(String(64), comment='申请单id')
    PRid = Column(String(64), nullable=False, comment='申请猜数字的商品id')
    PRmainpic = Column(String(255), nullable=False, comment='主图', url=True)
    PRtitle = Column(String(255), nullable=False, comment='商品标题')
    PBid = Column(String(64), nullable=False, comment='品牌id')
    PBname = Column(String(64), nullable=False, comment='品牌名字')
    PRattribute = Column(String(255), comment='商品属性 ["网络","颜色","存储"]')
    PRdescription = Column(Text, comment='描述')
    PRfeight = Column(Float, default=0, comment='快递费用')
    PRprice = Column(Float, nullable=False, comment='显示价格')


class GuessNumAwardSku(Base):
    __tablename__ = 'GuessNumAwardSku'
    GNASid = Column(String(64), primary_key=True)
    GNAPid = Column(String(64), comment='申请商品id')
    SKUid = Column(String(64), nullable=False, comment='skuid')
    SKUprice = Column(DECIMAL(precision=28, scale=2), nullable=False, comment='sku价格')
    SKUstock = Column(Integer, comment='库存')
    SKUdiscountone = Column(DECIMAL(precision=28, scale=2), nullable=False, comment='sku折扣1')
    SKUdiscounttwo = Column(DECIMAL(precision=28, scale=2), nullable=False, comment='sku折扣2')
    SKUdiscountthree = Column(DECIMAL(precision=28, scale=2), nullable=False, comment='sku折扣3')
    SKUdiscountfour = Column(DECIMAL(precision=28, scale=2), nullable=False, comment='sku折扣4')
    SKUdiscountfive = Column(DECIMAL(precision=28, scale=2), nullable=False, comment='sku折扣5')
    SKUdiscountsix = Column(DECIMAL(precision=28, scale=2), nullable=False, comment='sku折扣6')


class MagicBoxApply(Base):
    """魔盒商品"""
    __tablename__ = 'MagicBoxApply'
    MBAid = Column(String(64), primary_key=True)
    SUid = Column(String(64), comment='发布者id')
    PRid = Column(String(64), nullable=False, comment='商品id')
    MBAday = Column(Date, nullable=False, comment='上架日')
    MBAfreight = Column(DECIMAL(precision=10, scale=2), default=0, comment='运费')
    Gearsone = Column(String(64), nullable=False, comment='第一档 [10-20]')
    Gearstwo = Column(String(64), nullable=False, comment='第二档 [10-20, 20-90]')
    Gearsthree = Column(String(64), nullable=False, comment='第三档 [10-20, 30-90]')
    MBAstatus = Column(Integer, default=0, comment='申请状态, -10: 拒绝 0: 待审核, 10: 通过')
    MBArejectReason = Column(String(64), comment='拒绝理由')


class MagicBoxApplySku(Base):
    """魔盒商品sku"""
    __tablename__ = 'MagicBoxApplySku'
    MBSid = Column(String(64), primary_key=True)
    MBAid = Column(String(64), nullable=False, comment='魔盒商品id')
    SKUid = Column(String(64), nullable=False, comment='原商品skuid')
    SKUprice = Column(DECIMAL(precision=28, scale=2), nullable=False, comment='价格')
    MBSstock = Column(BIGINT, comment='库存')
    HighestPrice = Column(DECIMAL(precision=28, scale=2), nullable=False, comment='最高可购价格')
    LowestPrice = Column(DECIMAL(precision=28, scale=2), nullable=False, comment='最低可购价格')


class MagicBoxJoin(Base):
    """魔盒"""
    __tablename__ = 'MagicBoxJoin'
    MBJid = Column(String(64), primary_key=True)
    USid = Column(String(64), nullable=False, comment='参与用户')
    MBAid = Column(String(64), nullable=False, comment='魔盒商品id')
    MBSid = Column(String(64), nullable=False, comment='所选魔盒skuid')
    PRtitle = Column(String(255), nullable=False, comment='标题')
    PRmainpic = Column(String(255), comment='主图', url=True)
    MBJstatus = Column(Integer, default=0, comment='-10:失效 0: 正在进行, 10 已完成')
    MBJprice = Column(DECIMAL(precision=28, scale=2), nullable=False, comment='原价格')
    MBJcurrentPrice = Column(DECIMAL(precision=28, scale=2), default=MBJprice, comment='当前价格')
    HighestPrice = Column(DECIMAL(precision=28, scale=2), nullable=False, comment='最高价格')
    LowestPrice = Column(DECIMAL(precision=28, scale=2), nullable=False, comment='最低价格')
    MBSendtime = Column(Date, nullable=False, comment='结束日')
    OMid = Column(String(64), comment='购买后的订单id')
    ACDid = Column(String(64), comment='活动押金id')


class MagicBoxOpen(Base):
    """拆盒记录"""
    __tablename__ = 'MagixBoxOpen'
    MBOid = Column(String(64), primary_key=True)
    USid = Column(String(64), nullable=False, comment='拆盒子之人')
    USname = Column(String(64), nullable=False, comment='拆盒子之人的用户名')
    USheader = Column(Text, default='用户头像', url=True)
    MBJid = Column(String(64), nullable=False, comment='所拆盒子')
    MBOgear = Column(Integer, nullable=False, comment='选择档位 {1,2,3}')
    MBOresult = Column(Float, nullable=False, comment='本次拆盒结果变动金额, 如 0.25')
    MBOaction = Column(Integer, default=0, comment='拆盒结果 {0: 减少 10：增加}')
    MBOprice = Column(Float, nullable=False, comment='此时价格')


class FreshManFirstApply(Base):
    """新人首单申请"""
    __tablename__ = 'FreshManFirstApply'
    FMFAid = Column(String(64), primary_key=True)
    SUid = Column(String(64), primary_key=True, comment='供应商')
    FMFAstartTime = Column(Date, nullable=False, comment='申请开始时间')
    FMFAendTime = Column(Date, nullable=False, comment='申请结束时间')
    FMFAfrom = Column(Integer, comment='来源 10: 供应商, 0平台管理员')
    FMFAstatus = Column(Integer, default=0, comment='申请状态, 0: 未处理, -10: 拒绝, 10: 通过')
    ADid = Column(String(64), comment='处理人')
    FMFArejectReson = Column(String(255), comment='拒绝理由')
    AgreeStartime = Column(Date, default=FMFAstartTime, comment='最终确认起始时间')  # 同意之后不可为空
    AgreeEndtime = Column(Date, default=FMFAendTime, comment='最终确认结束时间')


class FreshManFirstProduct(Base):
    """新人首单申请商品"""
    __tablename__ = 'FreshManFirstProduct'
    FMFPid = Column(String(64), primary_key=True)
    FMFAid = Column(String(64), nullable=False, comment='新人首单申请单id')
    PRid = Column(String(64), nullable=False, comment='申请新人首单的商品id')
    PRmainpic = Column(String(255), nullable=False, comment='主图', url=True)
    PRtitle = Column(String(255), nullable=False, comment='商品标题')
    PBid = Column(String(64), nullable=False, comment='品牌id')
    PBname = Column(String(64), nullable=False, comment='品牌名字')
    PRattribute = Column(String(255), comment='商品属性 ["网络","颜色","存储"]')
    PRdescription = Column(Text, comment='描述')
    PRfeight = Column(Float, default=0, comment='快递费用')
    PRprice = Column(Float, nullable=False, comment='显示价格')


class FreshManFirstSku(Base):
    """新人首单申请sku"""
    __tablename__ = 'FreshManFirstSku'
    FMFSid = Column(String(64), primary_key=True)
    FMFPid = Column(String(64), nullable=False, comment='申请商品id')
    FMFPstock = Column(Integer, default=1, comment='库存')
    SKUid = Column(String(64), nullable=False, comment='skuid')
    SKUprice = Column(Float, nullable=False, comment='sku价格')


class FreshManJoinFlow(Base):
    """新人首单参与记录"""
    __tablename__ = 'FreshManJoinFlow'
    FMJFid = Column(String(64), primary_key=True)
    OMid = Column(String(64), nullable=False, comment='订单id')
    OMprice = Column(Float, nullable=False, comment='订单价格')
    UPid = Column(String(64), comment='首单页面来源用户id, 以便分发奖励')


class SignInAward(Base):
    """签到设置表"""
    __tablename__ = 'SignInAward'
    SIAid = Column(String(64), primary_key=True)
    SIAday = Column(Integer, comment='持续天数')
    SIAnum = Column(Integer, comment='累加积分')
    

class OutStock(Base):
    """活动sku出库单, 减少改动, 仅魔盒和猜数字使用"""
    __tablename__ = 'OutStock'
    OSid = Column(String(64), primary_key=True)
    SKUid = Column(String(64), nullable=False, comment='出库sku')
    OSnum = Column(BIGINT, default=1, comment='活动出库数量')


class TimeLimitedActivity(Base):
    """限时活动"""
    __tablename__ = 'TimeLimitedApply'
    TLAid = Column(String(64), primary_key=True)
    TLAstartTime = Column(DateTime, comment='活动开始时间')
    TLAendTime = Column(DateTime, comment='活动结束时间')
    TLAstatus = Column(Integer, default=0, comment='活动状态, 0: 发布, -10: 中止, 10: 结束')
    ADid = Column(String(64), comment='处理人')
    TLAsort = Column(Integer, comment='权重')
    TLAtopPic = Column(Text, url=True, comment='活动背景图')
    TlAname = Column(Text, comment='活动名称')
    # AgreeStartime = Column(DateTime, default=TLAstartTime, comment='最终确认起始时间')  # 同意之后不可为空
    # AgreeEndtime = Column(DateTime, default=TLAendTime, comment='最终确认结束时间')


class TimeLimitedProduct(Base):
    """限时活动商品"""
    __tablename__ = 'TimeLimitedProduct'
    TLPid = Column(String(64), primary_key=True)
    TLAid = Column(String(64), comment='活动单id')
    TLAfrom = Column(Integer, comment='来源 10: 供应商, 0平台管理员')
    SUid = Column(String(64), comment='供应商')
    PRid = Column(String(64), comment='商品id')
    TLArejectReson = Column(String(255), comment='拒绝理由')
    TLAstatus = Column(Integer, default=0, comment='申请状态, 0: 未处理, -10: 拒绝, 10: 通过')
    # PRmainpic = Column(String(255), nullable=False, comment='主图', url=True)
    # PRtitle = Column(String(255), nullable=False, comment='商品标题')
    # PBid = Column(String(64), nullable=False, comment='品牌id')
    # PBname = Column(String(64), nullable=False, comment='品牌名字')
    # PRattribute = Column(String(255), comment='商品属性 ["网络","颜色","存储"]')
    # PRdescription = Column(Text, comment='描述')
    # PRfeight = Column(Float, default=0, comment='快递费用')
    PRprice = Column(Float, nullable=False, comment='显示价格')


class TimeLimitedSku(Base):
    """限时活动sku"""
    __tablename__ = 'TimeLimitedSku'
    TLSid = Column(String(64), primary_key=True)
    TLPid = Column(String(64), comment='申请商品id')
    TLSstock = Column(String(64), comment='库存')
    SKUid = Column(String(64), comment='skuid')
    SKUprice = Column(DECIMAL(precision=28, scale=2), comment='sku价格')


class GuessGroup(Base):
    """竞猜团"""
    __tablename__ = 'GuessGroup'
    GGid = Column(String(64), primary_key=True)
    USid = Column(String(64), nullable=False, comment='发起人')
    GPid = Column(String(64), comment='拼团商品')
    PRtitle = Column(String(255), nullable=False, comment='标题')
    PRmainpic = Column(String(255), comment='主图', url=True)
    GPdeposit = Column(DECIMAL(precision=10, scale=2), comment='押金')
    GGstarttime = Column(DateTime, nullable=False, comment='拼团开始时间')
    GGendtime = Column(DateTime, nullable=False, comment='拼团结束时间')
    GGstatus = Column(Integer, default=0, comment='拼团状态 {拼团失败:-10, 等待分享:0, 等待开奖:10 购买成功:20}')
    GGcorrectNum = Column(Integer, comment='开奖时的正确数字')


class GuessRecord(Base):
    """竞猜拼团记录"""
    __tablename__ = 'GuessRecord'
    GRid = Column(String(64), primary_key=True)
    GGid = Column(String(64), nullable=False, comment='拼团id')
    GPid = Column(String(64), nullable=False, comment='商品id')
    GRnumber = Column(Integer, nullable=False, comment='竞猜数字')
    GRdigits = Column(Integer, comment='数字位数 个位:0 十位:10 百位:20')
    USid = Column(String(64), nullable=False, comment='竞猜者')
    UShead = Column(Text, url=True, comment='用户头像')
    USname = Column(Text, comment='用户昵称')
    OMid = Column(String(64), comment='订单id')
    GRstatus = Column(Integer, default=0, comment='竞猜状态 {失效:-10 ; 有效: 0 ')


class GroupGoodsProduct(Base):
    """拼团商品"""
    __tablename__ = 'GroupGoodsProduct'
    GPid = Column(String(64), primary_key=True)
    SUid = Column(String(64), nullable=False, comment='发布者id')
    PRid = Column(String(64), comment='商品id')
    GPfreight = Column(DECIMAL(precision=10, scale=2), default=0, comment='运费')
    GPstatus = Column(Integer, default=0, comment='申请状态, -10: 拒绝 0: 待审核, 10: 通过')
    GPrejectReason = Column(String(255), comment='拒绝理由')
    GPday = Column(Date, comment='开始日期')


class GroupGoodsSku(Base):
    """拼团商品sku"""
    __tablename__ = 'GroupGoodsSku'
    GSid = Column(String(64), primary_key=True)
    GPid = Column(String(64), comment='拼团商品id')
    SKUid = Column(String(64), comment='普通商品skuid')
    GSstock = Column(BIGINT, comment='拼团库存')
    SKUPrice = Column(DECIMAL(precision=28, scale=2), nullable=False, comment='sku原价格')
    SKUFirstLevelPrice = Column(DECIMAL(precision=28, scale=2), nullable=False, comment='猜对一个数字时的价格')
    SKUSecondLevelPrice = Column(DECIMAL(precision=28, scale=2), nullable=False, comment='猜对两个数字时的价格')
    SKUThirdLevelPrice = Column(DECIMAL(precision=28, scale=2), nullable=False, comment='猜对三个数字时的价格')
    # OSid = Column(String(64), nullable=False, comment='库存单')
    #
    # @property
    # def GSstock(self):
    #     from flask import current_app
    #     current_app.logger.info('>>> 调用了GSstock<<<')
    #     out_stock = OutStock.query.filter(OutStock.OSid == self.OSid,
    #                                       OutStock.isdelete == False, ).first()
    #     if out_stock:
    #         return out_stock.OSnum
