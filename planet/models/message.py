from sqlalchemy import String, Text, Integer, Boolean, DateTime
from sqlalchemy.dialects.mysql import LONGTEXT

from planet.common.base_model import Base, Column


class PlatformMessage(Base):
    """站内信"""
    PMid = Column(String(64), primary_key=True)
    PMtext = Column(LONGTEXT, comment='站内信内容')
    PMtitle = Column(Text, comment='站内信标题')
    PMcreate = Column(String(64), comment='创建人')
    PMfrom = Column(Integer, default=0, comment='0 平台发布 10 店主发布')
    PMstatus = Column(Integer, default=0, comment='0 草稿 1 上线 2 隐藏')


class UserPlatfromMessage(Base):
    """个人站内信"""
    UPMid = Column(String(64), primary_key=True)
    PMid = Column(String(64), comment='站内信id')
    USid = Column(String(64), comment='用户id')
    UPMstatus = Column(Integer, default=0, comment='0 未读 1 已读')


class UserPlatfromMessageLog(Base):
    """个人站内信阅读记录"""
    UPMLid = Column(String(64), primary_key=True)
    UPMid = Column(String(64), comment='站内信id')
    USid = Column(String(64), comment='用户id')
