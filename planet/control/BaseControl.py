import uuid
import datetime
from decimal import Decimal

from flask import request

from planet.config.cfgsetting import ConfigSettings
from planet.config.enums import ApprovalType, ApplyStatus, ApprovalAction
from planet.common.error_response import SystemError
from planet.common.request_handler import gennerc_log
from planet.extensions.register_ext import db
from planet.models import User
from planet.models.approval import Approval, ApprovalNotes, Permission
from planet.service.SApproval import SApproval


class BASEAPPROVAL():
    sapproval = SApproval()

    def create_approval(self, avtype, startid, avcontentid):
        # avtype = int(avtype)
        pt = Permission.query.filter_by_(PTid=avtype).first_('参数异常')
        av = Approval.create({
            "AVid": str(uuid.uuid1()),
            "AVname": avtype + datetime.datetime.now().strftime('%Y%m%d%H%M%S'),
            "PTid": avtype,
            "AVstartid": startid,
            "AVlevel": 1,
            "AVstatus": ApplyStatus.wait_check.value,
            "AVcontent": avcontentid
        })
        with self.sapproval.auto_commit() as s:
            user = User.query.filter_by_(USid=startid).first_('数据异常')
            aninstance = ApprovalNotes.create({
                "ANid": str(uuid.uuid1()),
                "AVid": av.AVid,
                "ADid": startid,
                "ANaction": ApprovalAction.submit.value,
                "AVadname": user.USname,
                "ANabo": "发起申请"
            })
            s.add(av)
            s.add(aninstance)
        return av.AVid



