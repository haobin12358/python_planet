import uuid
import json

from werkzeug.security import generate_password_hash

from planet.common.error_response import AuthorityError
from planet.common.success_response import Success
from planet.common.token_handler import admin_required, is_admin, is_supplizer, token_required
from planet.extensions.register_ext import db
from planet.extensions.validates.user import SupplizerListForm, SupplizerCreateForm, SupplizerGetForm, \
    SupplizerUpdateForm
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

    def update(self):
        """更新供应商信息"""
        if not is_admin() and not is_supplizer():
            raise AuthorityError()
        form = SupplizerUpdateForm().valid_data()
        with db.auto_commit():
            supplizer = Supplizer.query.filter(
                Supplizer.isdelete == False,
                Supplizer.SUid == form.suid.data
            ).first_('供应商不存在')
            supplizer.update({
                'SUlinkPhone': form.sulinkphone.data,
                'SUloginPhone': form.suloginphone.data,
                'SUname': form.suname.data,
                'SUlinkman': form.sulinkman.data,
                'SUaddress': form.suaddress.data,
                'SUbanksn': form.subanksn.data,
                'SUbankname': form.subankname.data,
                # 'SUpassword': generate_password_hash(form.supassword.data),
                'SUheader': form.suheader.data,
                'SUcontract': form.sucontract.data,
            }, null='dont ignore')
            db.session.add(supplizer)
        return Success('更新成功')

    @token_required
    def get(self):
        if not is_admin() and not is_supplizer():
            raise AuthorityError()
        form = SupplizerGetForm().valid_data()
        supplizer = form.supplizer
        supplizer.hide('SUpassword')
        return Success(data=supplizer)


