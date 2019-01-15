import json

from sqlalchemy import String, DECIMAL, Integer

from planet.common.base_model import Base, Column
from planet.common.error_response import StatusError


class Commision(Base):
    __tablename__ = 'Commision'
    COid = Column(String(64), primary_key=True)
    Levelcommision = Column(String(32), default='["0", "0", "0", "0"]', comment='佣金比例: 1级, 2级, 3级, 平台')
    # 升级相关
    InviteNum = Column(Integer, default=0, comment='升级所需人数')
    GroupSale = Column(DECIMAL(precision=28, scale=2), comment='升级所需团队总额')
    PesonalSale = Column(DECIMAL(precision=28, scale=2), comment='升级所需个人总额')
    InviteNumScale = Column(DECIMAL(scale=2), default=1, comment='下次升级/上次升级 比例')
    GroupSaleScale = Column(DECIMAL(scale=2), default=1, comment='下次升级/上次升级 比例')
    PesonalSaleScale = Column(DECIMAL(scale=2), default=1, comment='下次升级/上次升级 比例')
    # 级差相关
    ReduceRatio = Column(String(32), default='["0", "0", "0", "0"]', comment='级差减额, 共四级')
    IncreaseRatio = Column(String(32), default='["0", "0", "0", "0"]', comment='级差增额')

    @classmethod
    def devide_rate_baseline(cls):
        commision = cls.query.filter(cls.isdelete == False).first()
        if commision:
            level_commision = json.loads(commision.Levelcommision)
            return level_commision[-1]
        raise StatusError('项目需要初始化')

    @classmethod
    def level_commisions(cls):
        commision = cls.query.filter(cls.isdelete == False).first()
        if commision:
            level_commision = json.loads(commision.Levelcommision)
            return level_commision
        raise StatusError('项目需要初始化')


