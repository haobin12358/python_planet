# -*- coding: utf-8 -*-
from sqlalchemy import Integer, String
from planet.common.base_model import Base, Column


class TrialCommodity(Base):
    """试用商品"""
    __tablename__ = 'TrialCommodity'
    TCid = Column(String(64), primary_key=True)
