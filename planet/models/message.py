from sqlalchemy import String, Text, Integer, Boolean
from sqlalchemy.dialects.mysql import LONGTEXT

from planet.common.base_model import Base, Column


class PlatformMessage(Base):
    PMid = Column(String(64), primary_key=True)
    PMtext = Column(LONGTEXT, comment='站内信内容')
    PMcreate = Column(String(64), comment='创建人')
    PMstatus = Column(Integer, default=0, comment='0 草稿 1 上线 2 隐藏')


class UserPlatfromMessage(Base):
    UPMid = Column(String(64), primary_key=True)
    PMid = Column(String(64), comment='站内信id')
    USid = Column(String(64), comment='用户id')
    UPMstatus = Column(Integer, default=0, comment='0 未读 1 已读')

