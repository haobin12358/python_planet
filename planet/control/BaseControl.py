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
    def __init__(self, total_price=None, total_comm=None, commision=None, one_level_commission=None):
        """

        :param total_price: 总价
        :param total_comm: 总佣金
        :param commision: 配置文件中的佣金比例
        :param one_level_commission: 一级佣金比例
        """
        self.total_price = total_price
        self.commision = str(commision or self.default_commision())
        self.total_comm = total_comm or self.catulate_total_comm()
        self.one_level_commission = str(one_level_commission)

    def default_commision(self):
        """
        :return: string
        """
        return ConfigSettings().get_item('commission', 'planetcommision')

    def caculate_up_comm(self, up2=None):
        """计算佣金"""
        self.up2_comm = 0
        if up2:
            self.up1_comm = self.total_comm * (Decimal(self.one_level_commission) / 100)
            self.up2_comm = self.total_comm - self.up1_comm
        else:
            self.up1_comm = self.total_comm
        return self.up1_comm, self.up2_comm

    def insert_into_order_main(self, omid):
        pass
        # 佣金
        # 添加预计到帐佣金(两级)
        # 佣金写入主单

    def catulate_total_comm(self):
        """计算总佣金"""
        return Decimal(str(self.total_price)) * (Decimal(self.commision) / 100)






