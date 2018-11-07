# -*- coding: utf-8 -*-
from datetime import datetime

from sqlalchemy import Column, Integer, String, Text, Float, DateTime, Boolean

from planet.common.base_model import Base


class IdentifyingCode(Base):
    """验证码"""
    __tablename__ = "identifyingcode"
    ICid = Column(String(64), primary_key=True)
    ICtelphone = Column(String(14), nullable=False)  # 获取验证码的手机号
    ICcode = Column(String(8), nullable=False)    # 获取到的验证码

