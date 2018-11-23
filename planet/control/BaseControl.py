import uuid
import datetime
from decimal import Decimal

from planet.config.cfgsetting import ConfigSettings
from planet.config.enums import ApprovalType
from planet.common.error_response import SystemError
from planet.common.request_handler import gennerc_log
from planet.models.approval import Approval, ApprovalNotes
from planet.service.SApproval import SApproval


class BASEAPPROVAL():
    sapproval = SApproval()

    def create_approval(self, avtype, startid, avcontentid):
        avtype = int(avtype)

        av = Approval.create({
            "AVid": str(uuid.uuid1()),
            "AVname": ApprovalType(avtype).name + datetime.datetime.now().strftime('%Y%m%d%H%M%S'),
            "AVtype": avtype,
            "AVstartid": startid,
            "AVlevel": 1,
            "AVstatus": 0,
            "AVcontent": avcontentid
        })
        with self.sapproval.auto_commit() as s:
            aninstance = ApprovalNotes.create({
                "ANid": str(uuid.uuid1()),
                "AVid": av.AVid,
                "ANaction": 0,
                "ANabo": "发起申请"
            })
            s.add(av)
            s.add(aninstance)


class Commsion:
    def __init__(self, user, total_price=None):
        """
        :param total_price: 总价(元)
        :param user 用户
        """
        self.total_price = total_price
        self.user = user

    def default_commision(self, level=1):
        """
        :return: string
        """
        cfg = ConfigSettings()
        if level == 1:
            return cfg.get_item('commission', 'level1commision')
        elif level == 2:
            return cfg.get_item('commission', 'level2commision')

    @property
    def level1commision(self):
        return self.user.USCommission1 or self.default_commision(1)

    @property
    def level2commision(self):
        return self.user.USCommission2 or self.default_commision(2)








