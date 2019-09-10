from sqlalchemy import String, Text, Integer, DECIMAL, Boolean
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
    PLid = Column(String(64), comment='活动id')
    AuthorID = Column(String(64), nullable=False, comment='作者')
    AuthorType = Column(Integer, default=20, comment='作者身份 {20:用户 0: 平台}')
    TRproducts = Column(Text, comment='推荐商品 list')
    TRsort = Column(Integer, comment='攻略排序')
    TRbudget = Column(DECIMAL(precision=28, scale=2), comment='预算')
    TRcontent = Column(LONGTEXT, comment='内容')
    TRtitle = Column(String(255), comment='游记标题')
    TRlocation = Column(Text, comment='景区')
    TRtype = Column(Integer, default=0, comment='类别 {0: 攻略 1: 游记 3: 随笔}')
    TRstatus = Column(Integer, default=0, comment='状态 {0：草稿 1：已发布}')


class CustomizeShareContent(Base):
    """自定义团队广场分享内容"""
    __tablename__ = 'CustomizeShareContent'
    CSCid = Column(String(64), primary_key=True)
    USid = Column(String(64), comment='用户')
    PLid = Column(String(64), comment='活动id')
    Album = Column(LONGTEXT, comment='分享相册 json')
    TRids = Column(Text, comment='trid json')
    Detail = Column(Boolean, default=True, comment='活动详情')
    CSCtype = Column(Integer, default=1, comment='类型 1：分享相册 2：分享团队广场页面')


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


class Toilet(Base):
    """厕所"""
    __tablename__ = 'Toilet'
    TOid = Column(String(64), primary_key=True)
    creatorID = Column(String(64), comment='发布者id')
    creatorType = Column(Integer, comment='发布者身份 {20:用户 0: 平台}')
    longitude = Column(String(64), comment='经度')
    latitude = Column(String(64), comment='维度')
    TOimage = Column(Text, comment='厕所图片')
    TOstatus = Column(Integer, default=0, comment='审核状态 ApprovalAction 1：通过 0：审核中 -1：未通过')
