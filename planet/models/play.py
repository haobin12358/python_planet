from sqlalchemy import String, Text, DateTime, Integer, DECIMAL
from sqlalchemy.dialects.mysql import LONGTEXT

from planet.common.base_model import Base, Column


class Play(Base):
    """小程序活动"""
    __tablename__ = 'Play'
    PLid = Column(String(64), primary_key=True)
    PLname = Column(Text, comment='活动名')
    PLimg = Column(Text, comment='活动图')
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
    INcost = Column(DECIMAL, comment='保险费')


class Cost(Base):
    """活动费用明细表"""
    __tablename__ = 'Cost'
    COSid = Column(String(64), primary_key=True)
    PLid = Column(String(64), comment='活动id')
    COSname = Column(String(256), comment='费用名')
    COSsubtotal = Column(DECIMAL, comment='费用小计')
    COSdetail = Column(Text, comment='费用说明')


class Gather(Base):
    """集合"""
    __tablename__ = 'Gather'
    GAid = Column(String(64), primary_key=True)
    PLid = Column(String(64), comment='活动id')
    GAlon = Column(String(64), comment='经度')
    GAlat = Column(String(64), comment='维度')
    GAcreate = Column(String(64), comment='发起人')
