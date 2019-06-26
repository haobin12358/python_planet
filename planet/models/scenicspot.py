from sqlalchemy import String, Text, Integer, DECIMAL
from sqlalchemy.dialects.mysql import LONGTEXT

from planet.common.base_model import Base, Column


class ScenicSpot(Base):
    __tablename__ = 'ScenicSpot'
    SSPid = Column(String(64), primary_key=True)
    AAid = Column(String(64), comment='区域id')
    SSPcontent = Column(LONGTEXT, comment='景区介绍')
    SSPname = Column(Text, comment='景区名')
    SSPlevel = Column(Integer, default=5, comment='景区等级')
    SSPmainimg = Column(Text, comment='景区主图')
    ParentID = Column(String(64), comment='父id')


class TouristGuide(Base):
    __tablename__ = 'TouristGuide'
    TGid = Column(String(64), primary_key=True)
    TGcity = Column(String(512), comment=' 城市')
    TGproducts = Column(Text, comment='推荐商品 list')
    TGsort = Column(Integer, comment='攻略排序')
    TGbudget = Column(DECIMAL(precision=28, scale=2), comment='预算')
    TGcontent = Column(LONGTEXT, comment='内容')
    TGscenicSpot = Column(Text, comment='关联景区')
