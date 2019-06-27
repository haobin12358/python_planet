from sqlalchemy import String, Text, Integer, DECIMAL
from sqlalchemy.dialects.mysql import LONGTEXT

from planet.common.base_model import Base, Column


class ScenicSpot(Base):
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


class TouristGuide(Base):
    __tablename__ = 'TouristGuide'
    TGid = Column(String(64), primary_key=True)
    AuthorID = Column(String(64), nullable=False, comment='作者')
    AuthorType = Column(Integer, comment='作者身份')
    TGcity = Column(String(512), comment=' 城市')
    TGproducts = Column(Text, comment='推荐商品 list')
    TGsort = Column(Integer, comment='攻略排序')
    TGbudget = Column(DECIMAL(precision=28, scale=2), comment='预算')
    TGcontent = Column(LONGTEXT, comment='内容')
    TGscenicSpot = Column(Text, comment='关联景区')
    TGtype = Column(Integer, default=0, comment='类别 {0: 攻略 1: 游记}')
    TGstatus = Column(Integer, default=0, comment='状态 {0：草稿 1：已发布}')
