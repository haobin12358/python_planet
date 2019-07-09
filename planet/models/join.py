from sqlalchemy import Integer, Text, String, DECIMAL

from planet.common.base_model import Base, Column


class SignInSet(Base):
    """签到"""
    __tablename__ = 'SignInSet'
    SISid = Column(String(64), primary_key=True)
    PLid = Column(String(64), comment='活动id')
    SISstatus = Column(Integer, default=0, comment='签到状态')
    SILnum = Column(String(16), comment='签到码')


class SignInLog(Base):
    """签到记录"""
    __tablename__ = 'SignInLog'
    SILid = Column(String(64), primary_key=True)
    SISid = Column(String(64), comment='签到id')
    USid = Column(String(64), comment='用户id')
    SISstatus = Column(Integer, default=0, comment='签到状态 0 未签到 1 已签到')


class EnterLog(Base):
    """报名记录"""
    __tablename__ = 'EnterLog'
    ELid = Column(String(64), primary_key=True)
    PLid = Column(String(64), comment='活动id')
    USid = Column(String(64), comment='用户id')
    ELstatus = Column(Integer, default=0, comment='报名状态')
    ELvalue = Column(Text, comment='需求填写值, json ')
    ELpayNo = Column(String(64), comment='付款流水号')


class EnterCost(Base):
    """报名选择保险费用"""
    __tablename__ = 'EnterCost'
    ECid = Column(String(64), primary_key=True)
    ELid = Column(String(64), comment='报名记录id')
    ECcontent = Column(String(64), comment='保险或费用id')
    ECtype = Column(Integer, default=0, comment='费用类型 0 费用 1 保险')
    ECcost = Column(DECIMAL(precision=28, scale=2), comment='费用小计')


class UserItem(Base):
    """用户标签表"""
    __tablename__ = 'UserItem'
    UITid = Column(String(64), primary_key=True)
    USid = Column(String(64), comment='被评价人')
    ITid = Column(String(64), comment='标签id')
    UITcreate = Column(String(64), comment='评价人id')
    PLid = Column(String(64), comment='活动id')


class UserScore(Base):
    """领队评分表"""
    __tablename__ = 'UserScore'
    USCid = Column(String(64), primary_key=True)
    PLid = Column(String(64), comment='活动id')
    USid = Column(String(64), comment='领队id')
    USCnum = Column(Integer, default=10, comment='评分')
    USCcreate = Column(String(64), comment='创建人')


class HelpRecord(Base):
    """求救记录"""
    __tablename__ = 'HelpRecord'
    HRid = Column(String(64), primary_key=True)
    USid = Column(String(64), comment='求救人')
    UStelphone = Column(String(64), comment='求救人手机号')
    USlatitude = Column(String(64), comment='求救人所在纬度')
    USlongitude = Column(String(64), comment='求救人所在经度')
    PLid = Column(String(64), comment='活动id')
    HRphones = Column(Text, comment='求救的手机号，list')


class CancelApply(Base):
    """取消申请"""
    __tablename__ = 'CancelApply'
    CAPid = Column(String(64), primary_key=True)
    ELid = Column(String(64), comment='活动报名id')
    CAPstatus = Column(Integer, comment='申请状态')
    CAPreason = Column(Text, comment='申请原因')
