import uuid
import json

from werkzeug.security import generate_password_hash

from planet.common.success_response import Success
from planet.common.token_handler import admin_required
from planet.extensions.register_ext import db
from planet.extensions.validates.user import SupplizerListForm, SupplizerCreateForm, SupplizerGetForm
from planet.models import Supplizer


class CSupplizer:
    def __init__(self):
        pass

    @admin_required
    def list(self):
        """供应商列表"""
        form = SupplizerListForm().valid_data()
        kw = form.kw.data
        mobile = form.mobile.data

        supplizers = Supplizer.query.filter_by_().filter_(
            Supplizer.SUname.contains(kw),
            Supplizer.SUlinkPhone.contains(mobile)
        ).all_with_page()
        for supplizer in supplizers:
            supplizer.hide('SUpassword')
        return Success(data=supplizers)

    @admin_required
    def create(self):
        """添加"""
        form = SupplizerCreateForm().valid_data()
        with db.auto_commit():
            supperlizer = Supplizer.create({
                'SUid': str(uuid.uuid1()),
                'SUlinkPhone': form.sulinkphone.data,
                'SUloginPhone': form.suloginphone.data,
                'SUname': form.suname.data,
                'SUlinkman': form.sulinkman.data,
                'SUaddress': form.suaddress.data,
                'SUbanksn': form.subanksn.data,
                'SUbankname': form.subankname.data,
                'SUpassword': generate_password_hash(form.supassword.data),
                'SUheader': form.suheader.data,
                'SUcontract': form.sucontract.data,
            })
            db.session.add(supperlizer)
        return Success('创建成功', data={'suid': supperlizer.SUid})

    @admin_required
    def get(self):
        form = SupplizerGetForm().valid_data()
        supplizer = form.supplizer
        supplizer.hide('SUpassword')
        return Success(data=supplizer)


