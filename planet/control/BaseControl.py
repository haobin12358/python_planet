import uuid
import datetime
from planet.config.enums import ApprovalType
from planet.common.error_response import SystemError
from planet.common.request_handler import gennerc_log
from planet.models.approval import Approval


class BASEAPPROVAL():
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
            # todo 审批流创建流水记录
            s.add(av)
