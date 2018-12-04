from datetime import datetime

from planet.config.enums import ApplyStatus
from planet.models import FreshManFirstApply, Products


class CFreshManFirstOrder:
    def __init__(self):
        pass

    def list(self):
        """获取列表"""
        time_now = datetime.now()
        fresh_man_firsts = FreshManFirstApply.query.filter_by().filter_(
            FreshManFirstApply.FMFAstatus == ApplyStatus.agree.value,
            FreshManFirstApply.AgreeStartime <= time_now,
            FreshManFirstApply.AgreeEndtime >= time_now,
        ).all()
        for fresh_man_first in fresh_man_firsts:
            product = Products.query.filter_by()
            # todo
