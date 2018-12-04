from planet.common.success_response import Success
from planet.common.token_handler import admin_required
from planet.extensions.validates.user import SupplizerListForm, SupplizerCreateForm
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

