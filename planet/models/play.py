from sqlalchemy import String, Text, DateTime, Integer, DECIMAL
from sqlalchemy.dialects.mysql import LONGTEXT

from planet.common.base_model import Base, Column


class Play(Base):
    """小程序活动"""
    __tablename__ = 'Play'
    PLid = Column(String(64), primary_key=True)
    PLname = Column(Text, comment='活动名')
    PLimg = Column(Text, url=True, comment='活动图')
    PLstartTime = Column(DateTime, comment='活动开始时间')
    PLendTime = Column(DateTime, comment='活动结束时间')
    PLlocation = Column(Text, comment='活动地点,list')
    PLnum = Column(Integer, comment='最大承载人数')
    PLtitle = Column(String(128), comment='活动标题')
    PLcontent = Column(Text, comment='活动内容 json')
    PLcreate = Column(String(64), comment='创建人')
    PLstatus = Column(Integer, default=0, comment='活动状态 0 草稿 1 组队中 2 活动中 3 已关闭')
    PLproducts = Column(Text, comment='推荐携带商品 list')


class PlayNotice(Base):
    """活动公告"""
    __tablename__ = 'PlayNotice'
    PLNid = Column(String(64), primary_key=True)
    PLid = Column(String(64), comment='活动id')
    PLNcontent = Column(Text, comment='活动公告')


class PlayRequire(Base):
    """活动需求项"""
    __tablename__ = 'PlayRequire'
    PREid = Column(String(64), primary_key=True)
    PREname = Column(String(255), comment='需求名')
    PLid = Column(String(64), comment='活动id')
    PREsort = Column(Integer, default=1, comment='排序')


class Insurance(Base):
    """活动保险"""
    __tablename__ = 'Insurance'
    INid = Column(String(64), primary_key=True)
    PLid = Column(String(64), comment='活动id')
    INname = Column(String(1024), comment='保险名')
    INcontent = Column(LONGTEXT, comment='保险详情')
    INtype = Column(Integer, default=0, comment='保险类型 0 非必选 1 必选')
    INcost = Column(DECIMAL(precision=28, scale=2), comment='保险费')


class Cost(Base):
    """活动费用明细表"""
    __tablename__ = 'Cost'
    COSid = Column(String(64), primary_key=True)
    PLid = Column(String(64), comment='活动id')
    COSname = Column(String(256), comment='费用名')
    COSsubtotal = Column(DECIMAL(precision=28, scale=2), comment='费用小计')
    COSdetail = Column(Text, comment='费用说明')


class Gather(Base):
    """集合"""
    __tablename__ = 'Gather'
    GAid = Column(String(64), primary_key=True)
    PLid = Column(String(64), comment='活动id')
    GAlon = Column(String(64), comment='经度')
    GAlat = Column(String(64), comment='维度')
    GAcreate = Column(String(64), comment='发起人')
    GAtime = Column(DateTime, comment='集合时间')


class Notice(Base):
    """公告"""
    __tablename__ = 'Notice'
    NOid = Column(String(64), primary_key=True)
    PLid = Column(String(64), comment='活动')
    NOcontent = Column(Text, comment='公告内容')
    # NOstatus = Column(Integer, default=0, comment='公告状态 0 展示 1 已修改')


class MakeOver(Base):
    """转让"""
    __tablename__ = 'MakeOver'
    MOid = Column(String(64), primary_key=True)
    PLid = Column(String(64), comment='活动id')
    MOassignor = Column(String(64), comment='转让人')
    MOsuccessor = Column(String(64), comment='承接人')
    MOstatus = Column(Integer, default=0, comment='转让状态 0:转让中 1:承接 2: 已支付, -1 拒绝 -2 取消 ')
    MOpayNo = Column(String(64), comment='付款流水号')
    MOprice = Column(DECIMAL(precision=28, scale=2), comment='转让费')


class Agreement(Base):
    """协议"""
    __tablename__ = 'Agreement'
    AMid = Column(String(64), primary_key=True)
    AMcontent = Column(Text, comment='协议内容')
    AMtype = Column(Integer, default=0, comment='协议类型 0:转让协议 1: 退款规则 2：门票规则 3：活跃分规则')
    AMname = Column(String(256), comment='规则名')


class PlayDiscount(Base):
    """退团折扣"""
    __tablename__ = 'PlayDiscount'
    PDid = Column(String(64), primary_key=True)
    PLid = Column(String(64), comment='活动id')
    PDtime = Column(DateTime, comment='限制时间')
    PDdeltaDay = Column(Integer, comment='时间差值')
    PDdeltaHour = Column(Integer, comment='时间差值')
    PDprice = Column(DECIMAL(precision=28, scale=2), comment='退款金额')


class SuccessorSearchLog(Base):
    """转让人查询记录"""
    __tablename__ = 'SuccessorSearchLog'
    SSLid = Column(String(64), primary_key=True)
    MOassignor = Column(String(64), comment='查询人')
    MOsuccessor = Column(String(64), comment='承接人')
    USrealname = Column(String(255), comment='承接人真实姓名')
    UStelphone = Column(String(13), comment='手机号')
    USidentification = Column(String(24), comment='身份证号')
    PLid = Column(String(64), comment='活动id')


class PlayPay(Base):
    """小程序支付流水"""
    __tablename__ = 'PlayPay'
    PPid = Column(String(64), primary_key=True)
    PPpayno = Column(String(64), index=True, comment='交易号, 自己生成')  # 即out_trade_no
    PPpayType = Column(Integer, default=0, comment='支付原因 0 报名 10 承接活动 20 支付票务')
    PPcontent = Column(String(64), comment='关联id')
    PPpaytime = Column(DateTime, comment='付款时间')
    PPpayMount = Column(DECIMAL(precision=28, scale=2), comment='付款金额')
    PPpaysn = Column(String(64), comment='第三方支付流水')
    PPpayJson = Column(Text, comment='回调原文')
    PPpaymarks = Column(String(255), comment='备注')
