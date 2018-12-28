from sqlalchemy import String, DECIMAL, Integer

from planet.common.base_model import Base, Column


class Commision(Base):
    __tablename__ = 'Commision'
    COid = Column(String(64), primary_key=True)
    Level1commision = Column(DECIMAL(precision=28, scale=2), default=0, comment='1级佣金比例')
    Level2commision = Column(DECIMAL(precision=28, scale=2), default=0,)
    Level3commision = Column(DECIMAL(precision=28, scale=2), default=0,)
    PlanetCommision = Column(DECIMAL(precision=28, scale=2), default=0, comment='平台抽成')
    # 升级相关
    InviteNum = Column(Integer, default=0, comment='升级所需人数')
    GroupSale = Column(DECIMAL(precision=28, scale=2), comment='升级所需团队总额')
    PesonalSale = Column(DECIMAL(precision=28, scale=2), comment='升级所需个人总额')
    InviteNumOffest = Column(DECIMAL(scale=2), default=1, comment='下次升级/上次升级 比例')
    GroupSaleOffset = Column(DECIMAL(scale=2), default=1, comment='下次升级/上次升级 比例')
    PesonalSaleOffset = Column(DECIMAL(scale=2), default=1, comment='下次升级/上次升级 比例')
    # 级差相关




