import uuid
import datetime
from decimal import Decimal

from flask import request

from planet.config.cfgsetting import ConfigSettings
from planet.config.enums import ApprovalType, ApplyStatus, ApprovalAction, ApplyFrom
from planet.common.error_response import SystemError
from planet.common.request_handler import gennerc_log
from planet.extensions.register_ext import db
from planet.models import User, Supplizer, Admin, PermissionType
from planet.models.approval import Approval, ApprovalNotes, Permission
from planet.service.SApproval import SApproval


class BASEAPPROVAL():
    sapproval = SApproval()

    def create_approval(self, avtype, startid,  avcontentid, applyfrom=None):
        # avtype = int(avtype)
        gennerc_log('start create approval ptid = {0}'.format(avtype))
        pt = PermissionType.query.filter_by_(PTid=avtype).first_('参数异常')
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

            if applyfrom == ApplyFrom.supplizer.value:
                sup = Supplizer.query.filter_by_(SUid=startid).first()
                name = getattr(sup, 'SUname', '')
            elif applyfrom == ApplyFrom.platform.value:
                admin = Admin.query.filter_by_(ADid=startid).first()
                name = getattr(admin, 'ADname', '')
            else:
                user = User.query.filter_by_(USid=startid).first()
                name = getattr(user, 'USname', '')

            aninstance = ApprovalNotes.create({
                "ANid": str(uuid.uuid1()),
                "AVid": av.AVid,
                "ADid": startid,
                "ANaction": ApprovalAction.submit.value,
                "AVadname": name,
                "ANabo": "发起申请",
                "ANfrom": applyfrom
            })
            s.add(av)
            s.add(aninstance)
        return av.AVid



