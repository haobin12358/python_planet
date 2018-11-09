# -*- coding: utf-8 -*-
from sqlalchemy import Column, String
from planet.common.base_model import Base


class AddressProvince(Base):
    """省"""
    __tablename__ = 'AddressProvince'
    APid = Column(String(8), primary_key=True, comment='省id')
    APname = Column(String(20), nullable=False, comment='省名')


class AddressCity(Base):
    """市"""
    __tablename__ = 'AddressCity'
    ACid = Column(String(8), primary_key=True, comment='市id')
    ACname = Column(String(20), nullable=False, comment='市名')
    APid = Column(String(8), nullable=False, comment='省id')


class AddressArea(Base):
    """区县"""
    __tablename__ = 'AddressArea'
    AAid = Column(String(8), primary_key=True, comment='区县id')
    AAname = Column(String(32), nullable=False, comment='区县名')
    ACid = Column(String(8), nullable=False, comment='市名')

