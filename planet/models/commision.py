from sqlalchemy import String, DECIMAL, Integer

from planet.common.base_model import Base, Column


class Commision(Base):
    __tablename__ = 'Commision'
    COid = Column(String(64), primary_key=True)
    Levelcommision = Column(String(32), default='["0", "0", "0", "0"]', comment='佣金比例: 1, 2, 3, 平台')
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




