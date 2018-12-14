# -*- coding: utf-8 -*-
from sqlalchemy import Integer, String, Text, Float, DateTime, Boolean, orm

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
    OMfrom = Column(Integer, default=0, comment='来源: 0: 购物车, 10: 商品详情 20: 店主权限, 30: 猜数字奖品, 40: 新人商品, 50: 帮拆礼盒, 60: 试用商品')
    PBname = Column(String(32), nullable=False, comment='品牌名')
    PBid = Column(String(64), nullable=False, comment='品牌id')
    OMclient = Column(Integer, default=0, comment='下单设备: 0: 微信, 10: app')
    OMfreight = Column(Float, default=0, comment='运费')
    OMmount = Column(Float, nullable=False, comment='总价')
    OMtrueMount = Column(Float, nullable=False, comment='实际总价')
    OMstatus = Column(Integer, default=0, comment='订单状态 0待付款,10待发货,20待收货, 35 待评价, 30完成 -40取消交易')
    OMinRefund = Column(Boolean, default=False, comment='主单是否在售后状态')
    OMmessage = Column(String(255), comment='留言')
    # 收货信息
    OMrecvPhone = Column(String(11), nullable=False, comment='收货电话')
    OMrecvName = Column(String(11), nullable=False, comment='收货人姓名')
    OMrecvAddress = Column(String(255), nullable=False, comment='地址')
    PRcreateId = Column(String(64), comment='发布者id')  # 不用
    OMlogisticType = Column(Integer, default=0, comment='发货类型 0 正常发货, 10线上发货(无物流)')


class OrderPay(Base):
    """
    付款流水
    """
    __tablename__ = 'OrderPay'
    OPayid = Column(String(64), primary_key=True)
    OPayno = Column(String(64), index=True, comment='交易号, 自己生成')  # 即out_trade_no
    OPayType = Column(Integer, default=0, comment='支付方式 0 微信 10 支付宝')
    OPaytime = Column(DateTime, comment='付款时间')
    OPayMount = Column(Integer, comment='付款金额')
    OPaysn = Column(String(64), comment='第三方支付流水')
    OPayJson = Column(Text, comment='回调原文')
    OPaymarks = Column(String(255), comment='备注')


class OrderCoupon(Base):
    """
    订单-优惠券使用表
    """
    __tablename__ = 'OrderRaward'
    OCid = Column(String(64), primary_key=True)
    COid = Column(String(64), nullable=False, comment='优惠券id')
    OMid = Column(String(64), nullable=False, comment='主单id')
    OCreduce = Column(Float, nullable=False, comment='减额')


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
    OPsubTrueTotal = Column(Float, default=OPsubTotal, comment='依照价格比例计算出的使用优惠券后的价格')
    # OPsubReducePriceFrom = Column(String(64), comment='减少金额的成本承担者(代理商), 为空则为平台')
    OPisinORA = Column(Boolean, default=False, comment='是否在售后')
    # 卖家信息
    PRfrom = Column(Integer, default=0, comment='商品来源 0 平台发布 10 店主发布')
    UPperid = Column(String(64), comment='上级id')  # 方便查询下级
    UPperid2 = Column(String(64), comment='上上级id')
    # 指定佣金比, 用于活动的自定义设置
    USCommission1 = Column(Float, comment='一级佣金比')
    USCommission2 = Column(Float, comment='二级佣金比')

    @property
    def SKUpic(self):
        return self.PRmainpic


class OrderRefundApply(Base):
    """订单售后申请"""
    __tablename__ = 'OrderRefundApply'
    ORAid = Column(String(64), primary_key=True)
    ORAsn = Column(String(64), nullable=False, comment='售后申请编号')
    OMid = Column(String(64), comment='主单id')
    OPid = Column(String(64), comment='副单id')  # 如果opid不为空, 则说明是副单售后申请
    USid = Column(String(64), nullable=False, comment='用户id')
    ORAstate = Column(Integer, default=0, comment='类型: 0 退货退款 10 仅退款')
    ORAreason = Column(String(255), nullable=False, comment='退款原因')
    ORAmount = Column(Float, nullable=False, comment='退款金额')
    ORAaddtion = Column(String(255), comment='退款说明')
    ORaddtionVoucher = Column(Text, comment='退款说明图片', url_list=True)
    ORAproductStatus = Column(Integer, default=0, comment='0已收货, 10 未收货')
    ORAstatus = Column(Integer, default=0, comment='状态-20已取消 -10 拒绝 0 未审核 10审核通过')
    ORAcheckReason = Column(String(255), comment='审核原因')
    ORAcheckUser = Column(String(64), comment='审核人')
    ORAcheckTime = Column(DateTime, comment='审核时间')
    ORAnote = Column(String(255), comment='备注')


class DisputeType(Base):
    """售后纠纷的一些内置理由"""
    __tablename__ = 'DisputeType'
    DIid = Column(String(64), primary_key=True)
    DIname = Column(String(32), nullable=False, comment='纠纷类型文字')
    DIsort = Column(Integer, nullable=False, comment='顺序标志')
    DItype = Column(Integer, default=0, comment='适用的售后类型0: 退货退款 10 仅退款')


class OrderRefund(Base):
    """订单退货表"""
    __tablename__ = 'OrderRefund'
    ORid = Column(String(64), primary_key=True)
    OMid = Column(String(64), nullable=False, comment='订单id')
    OPid = Column(String(64), comment='附单id')
    ORAid = Column(String(64), nullable=False, index=True, comment='售后申请id')
    ORrecvname = Column(String(16), nullable=False, comment='收货人姓名')
    ORrecvphone = Column(String(11), nullable=False, comment='收货人手机')
    ORrecvaddress = Column(String(255), nullable=False, comment='收货地址')
    ORstatus = Column(Integer, default=0, comment='退货状态, 0 等待买家发货 10 等待卖家收货 20 已收货, 30 已退款 -10 已取消')
    # 物流信息
    ORlogisticCompany = Column(String(32), comment='物流公司')
    ORlogisticsn = Column(String(64), comment='物流单号')
    ORlogisticSignStatus = Column(Integer, default=0, comment='签收状态 1.在途中 2.正在派件 3.已签收 4.派送失败 -1 异常数据')
    ORlogisticData = Column(Text, comment='查询结果')
    ORlogisticLostResult = Column(Text, comment='物流最后结果')
    # 其他


class OrderRefundFlow(Base):
    """退款流水记录表"""
    __tablename__ = 'OrderRefundFlow'
    ORFid = Column(String(64), primary_key=True)
    ORAid = Column(String(64), nullable=False, comment='售后申请id')
    ORAmount = Column(Float, nullable=False, comment='退款金额, 一般与退款申请中的金额相同')
    OPayno = Column(String(64), nullable=False, comment='付款时时候的外部单号')
    OPayType = Column(String(64), default=0, comment='类型: 支付方式 0 微信 10 支付宝')
    ORFoutRequestNo = Column(String(64), default=ORFid, comment='标识一次退款请求，同一笔交易多次退款需要保证唯一')


class OrderEvaluation(Base):
    """订单评价"""
    __tablename__ = 'OrderEvaluation'
    OEid = Column(String(64), primary_key=True)
    USid = Column(String(64), nullable=False, comment='用户')
    USname = Column(String(255), comment='用户名')
    USheader = Column(Text, default='用户头像', url=True)
    OPid = Column(String(64), nullable=False, comment='订单副单id')
    OMid = Column(String(64), nullable=False, comment='订单主单id')
    PRid = Column(String(64), nullable=False, comment='商品id')
    SKUattriteDetail = Column(Text, nullable=False, comment='sku详情[]')
    OEtext = Column(String(255), nullable=False, default='此用户没有填写评价。', comment='评价内容')
    OEscore = Column(Integer, nullable=False, default=5, comment='五星评分')


class OrderEvaluationImage(Base):
    """订单评价图片"""
    __tablename__ = 'OrderEvaluationImage'
    OEIid = Column(String(64), primary_key=True)
    OEid = Column(String(64), nullable=False, comment='评价id')
    OEImg = Column(String(255), nullable=False, url=True, comment='图片url')
    OEIsort = Column(Integer, comment='图片顺序')


class OrderEvaluationVideo(Base):
    """订单评价视频"""
    __tablename__ = 'OrderEvaluationVideo'
    OEVid = Column(String(64), primary_key=True)
    OEid = Column(String(64), nullable=False, comment='评价id')
    OEVideo = Column(String(255), nullable=False, url=True, comment='视频url')
    OEVthumbnail = Column(String(255), nullable=False, url=True, comment='视频缩略图')


class OrderLogistics(Base):
    """订单物流"""
    __tablename__ = 'OrderLogistics'
    OLid = Column(String(64), primary_key=True)
    OMid = Column(String(64), nullable=False, comment='主单id')
    # OPid = Column(String(125), comment='副单物流')
    OLcompany = Column(String(32), nullable=False, comment='物流公司')
    OLexpressNo = Column(String(64), nullable=False, comment='物流单号')
    OLsearchStatus = Column(String(8), default=0, comment='物流查询状态(待用字段) polling:监控中，shutdown:结束，abort:中止，updateall：重新推送。')
    OLsignStatus = Column(Integer, default=0, comment='签收状态 1.在途中 2.正在派件 3.已签收 4.派送失败 -1 异常数据')
    OLdata = Column(Text, comment='查询结果')
    OLlastresult = Column(Text, comment='物流最后状态')


class LogisticsCompnay(Base):
    """快递公司"""
    __tablename__ = 'LogisticsCompnay'
    id = Column(Integer, autoincrement=True, primary_key=True)
    LCname = Column(String(64), nullable=False, comment='公司名称')
    LCcode = Column(String(64), nullable=False, index=True, comment='快递公司编码')
    LCfirstCharater = Column(String(1), nullable=False, index=True, comment='首字母')
    LCisCommon = Column(Boolean, default=False, comment='是否常用')

    @orm.reconstructor
    def __init__(self):
        self.fields = ['LCname', 'LCcode', ]


class Coupon(Base):
    """优惠券"""
    __tablename__ = 'Coupon'
    COid = Column(String(64), primary_key=True)

    COname = Column(String(32), nullable=False, comment='优惠券名字, 比如满100减50')
    COisAvailable = Column(Boolean, default=True, comment='是否有效')
    COcanCollect = Column(Boolean, default=True, comment='是否可以领取')
    COcollectNum = Column(Integer, default=0, comment='领取数量')
    COuseNum = Column(Integer, default=0, comment='可使用叠加数量, 0 表示无限制')
    COsendStarttime = Column(DateTime, comment='抢券时间起')
    COsendEndtime = Column(DateTime, comment='抢卷结束时间')
    COvalidStartTime = Column(DateTime, comment='有效起始时间')
    COvalidEndTime = Column(DateTime, comment='有效期结束时间')
    COdiscount = Column(Float, default=10, comment='折扣')
    COdownLine = Column(Float, default=0, comment='使用最低金额限制,0 为无限制')
    COsubtration = Column(Float, default=0, comment='优惠价格')
    COdesc = Column(String(255), comment='描述')
    COlimitNum = Column(Integer, default=0, comment='发放数量')
    COremainNum = Column(Integer, default=COlimitNum, comment='剩余数量, 有COlimitNum时才会生效')
    SUid = Column(String(64), comment='来源供应商, 如为空则为平台')


class CouponItem(Base):
    """优惠券标签中间表"""
    __tablename__ = 'CouponItem'
    CIid = Column(String(64), primary_key=True)
    COid = Column(String(64), nullable=False, comment='优惠券id')
    ITid = Column(String(64), nullable=False, comment='标签id')


class CouponUser(Base):
    """用户的优惠券"""
    __tablename__ = 'CouponUser'
    UCid = Column(String(64), primary_key=True)
    COid = Column(String(64), nullable=False, comment='优惠券id')
    USid = Column(String(64), nullable=False, comment='用户id')
    UCalreadyUse = Column(Boolean, default=False, comment='是否已经使用')
    UCstatus = Column(Integer, default=0, comment='状态: 10 禁用')


class CouponFor(Base):
    """优惠券的使用对象"""
    __tablename__ = 'CouponFor'
    CFid = Column(String(64), primary_key=True)
    PCid = Column(String(64), comment='限制使用商品分类')
    PRid = Column(String(64), comment='限制使用商品')
    PBid = Column(String(64), comment='限制使用品牌')  # pbid prid pcid 不可以同时存在
    COid = Column(String(64), comment='优惠券id')


class ActivationCodeApply(Base):
    """购买商品激活码申请提交"""
    __tablename__ = 'ActivationCodeApply'
    ACAid = Column(String(64), primary_key=True)
    USid = Column(String(64), nullable=False, comment='提交用户id')
    ACAname = Column(String(32), nullable=False, comment='收款人姓名')
    ACAbankSn = Column(String(32), nullable=False, comment='收款银行卡号')
    ACAbankname= Column(String(125), nullable=False, comment='开户行')
    ACAvouchers = Column(Text, url_list=True, comment='凭证列表')
    ACAapplyStatus = Column(Integer, default=0, comment='0, 审核中 10 已同意, -10 已拒绝')


class UserActivationCode(Base):
    """用户拥有的激活码"""
    __tablename__ = 'UserActivationCode'
    UACid = Column(String(64), primary_key=True)
    USid = Column(String(64), index=True, nullable=False, comment='拥有者')
    UACcode = Column(String(16), nullable=False, index=True, comment='激活码, 两个小写字母加5个数字')
    UACstatus = Column(Integer, default=0, comment='使用状态 0未使用, 10 已经使用 -10 不可用')
    UACuseFor = Column(String(64), comment='使用者')
    UACtime = Column(DateTime, comment='使用时间')


class ActivationCodeRule(Base):
    """激活码提交页的一些规则等"""
    __tablename__ = 'ActivationCodeRule'
    ACRid = Column(String(64), primary_key=True)
    ACRrule = Column(Text, comment='规则')
    ACRphone = Column(String(11), comment='电话')
    ACRaddress = Column(String(64), comment='地址')
    ACRname = Column(String(16), nullable=False, comment='收款人')
    ACRbankSn = Column(String(32), nullable=False, comment='卡号')
    ACRbankAddress = Column(String(125), nullable=False, comment='支行地址')
    ACRAgreeMent = Column(Text, comment='协议')
    ACRisShow = Column(Boolean, default=True, comment='是否显示')





# todo 激活码使用
# todo 各种审核人, 原因