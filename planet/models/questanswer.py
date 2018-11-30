# -*- coding: utf-8 -*-
from sqlalchemy import Integer, String, Text, Float, Boolean, DateTime, DECIMAL

from planet.common.base_model import Base, Column


class QuestOutline(Base):
    """问题大纲"""
    __tablename__ = 'QuestOutline'
    QOid = Column(String(64), primary_key=True)
    QOicon = Column(Text, comment='问题大纲icon')
    QOname = Column(Text, comment='问题大纲名称')
    QOcreateId = Column(String(64), comment='创建人id')


class Quest(Base):
    """问题"""
    __tablename__ = 'Quest'
    QUid = Column(String(64), primary_key=True)
    QOid = Column(String(64), comment='问题所属大纲')
    QUquest = Column(Text, comment='问题描述')
    QUcreateId = Column(String(64), comment='创建人id')


class Answer(Base):
    """答案"""
    __tablename__ = 'Answer'
    QAid = Column(String(64), primary_key=True)
    QUid= Column(String(64), comment='问题')
    QAcontent = Column(Text, comment='问题回答')
    QAcreateId = Column(String(64), comment='创建人id')


class AnswerUser(Base):
    """答案查看记录"""
    __tablename__ = 'AnswerUser'
    QAUid = Column(String(64), primary_key=True)
    QAid = Column(String(64), comment='答案')
    USid = Column(String(64), comment='查看人')
