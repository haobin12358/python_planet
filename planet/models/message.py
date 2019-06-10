from sqlalchemy import String, Text, Integer, Boolean, DateTime
from sqlalchemy.dialects.mysql import LONGTEXT

from planet.common.base_model import Base, Column


class PlatformMessage(Base):
    """站内信"""
    __tablename__ = 'PlatformMessage'
    PMid = Column(String(64), primary_key=True)
    PMtext = Column(LONGTEXT, comment='站内信内容')
    PMtitle = Column(Text, comment='站内信标题')
    PMcreate = Column(String(64), comment='创建人')
    PMfrom = Column(Integer, default=0, comment='0 平台发布 10 店主发布')
    PMstatus = Column(Integer, default=0, comment='0 草稿 1 上线 2 隐藏')


class UserPlatfromMessage(Base):
    """个人站内信"""
    __tablename__ = 'UserPlatfromMessage'
    UPMid = Column(String(64), primary_key=True)
    PMid = Column(String(64), comment='站内信id')
    USid = Column(String(64), comment='用户id')
    UPMstatus = Column(Integer, default=0, comment='0 未读 1 已读')


class UserPlatfromMessageLog(Base):
    """个人站内信阅读记录"""
    __tablename__ = 'UserPlatfromMessageLog'
    UPMLid = Column(String(64), primary_key=True)
    UPMid = Column(String(64), comment='站内信id')
    USid = Column(String(64), comment='用户id')


class UserMessage(Base):
    """用户通讯记录"""
    __tablename__ = 'UserMessage'
    UMSGid = Column(String(64), primary_key=True)
    # USsend = Column(String(64), comment='发送人')
    # USreceive = Column(String(64), comment='接受人')
    USid = Column(String(64), comment='发送人')
    ROid = Column(String(64), comment='房间号')
    UMSGtext = Column(LONGTEXT, comment='内容')



class UserRoom(Base):
    """用户对话房间"""
    __tablename__ = 'UserRoom'
    URid = Column(String(64), primary_key=True)
    USid = Column(String(64), comment='参加用户')
    ROid = Column(String(64), comment='房间号')


class Room(Base):
    """房间"""
    __tablename__ = 'Room'
    ROid = Column(String(64), primary_key=True)
