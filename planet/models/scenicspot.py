from sqlalchemy import String, Text, Integer, DECIMAL
from sqlalchemy.dialects.mysql import LONGTEXT

from planet.common.base_model import Base, Column


class ScenicSpot(Base):
    """景区"""
    __tablename__ = 'ScenicSpot'
    SSPid = Column(String(64), primary_key=True)
    ADid = Column(String(64), nullable=False, comment='发布者')
    AAid = Column(String(64), comment='区域id')
    SSParea = Column(String(255), comment='区域str')
    SSPcontent = Column(LONGTEXT, comment='景区介绍')
    SSPname = Column(Text, comment='景区名')
    SSPlevel = Column(Integer, default=5, comment='景区等级')
    SSPmainimg = Column(Text, url=True, comment='景区主图')
    ParentID = Column(String(64), comment='父id')


class TravelRecord(Base):
    """时光记录(攻略|游记|随笔)"""
    __tablename__ = 'TravelRecord'
    TRid = Column(String(64), primary_key=True)
    AuthorID = Column(String(64), nullable=False, comment='作者')
    AuthorType = Column(Integer, default=20, comment='作者身份 {20:用户 0: 平台')
    # TGcity = Column(String(512), comment=' 城市')
    TRproducts = Column(Text, comment='推荐商品 list')
    TRsort = Column(Integer, comment='攻略排序')
    TRbudget = Column(DECIMAL(precision=28, scale=2), comment='预算')
    TRcontent = Column(LONGTEXT, comment='内容')
    TRtitle = Column(String(255), comment='游记标题')
    TRlocation = Column(Text, comment='景区')
    TRtype = Column(Integer, default=0, comment='类别 {0: 攻略 1: 游记 3: 随笔}')
    TRstatus = Column(Integer, default=0, comment='状态 {0：草稿 1：已发布}')


class Guide(Base):
    """导游认证"""
    __tablename__ = 'Guide'
    GUid = Column(String(64), primary_key=True)
    USid = Column(String(64))
    GUrealname = Column(String(255), comment='用户真实姓名')
    GUtelphone = Column(String(13), comment='手机号')
    GUidentification = Column(String(24), comment='身份证号')
    GUimg = Column(Text, url=True, comment='导游认证图片')
    GUstatus = Column(Integer, default=0, comment='申请状态')
