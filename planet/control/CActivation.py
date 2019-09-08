from datetime import datetime

from flask import request

from planet.common.error_response import ParamsError, AuthorityError
from planet.common.params_validates import parameter_required
from planet.common.success_response import Success
from planet.common.token_handler import admin_required, get_current_admin, token_required, common_user, is_admin
from planet.config.enums import AdminActionS
from planet.control.BaseControl import BASEADMIN
from planet.extensions.register_ext import db
from planet.models import ActivationType, Activation


class CActivation():

    def __init__(self):
        self.base_admin = BASEADMIN()
        pass

    @admin_required
    def update_activationtype(self):
        data = parameter_required('attid')
        attid = data.pop('attid')
        with db.auto_commit():
            att = ActivationType.query.filter_by(ATTid=attid, isdelete=False).first_('活跃度获取方式未被记录')
            admin = get_current_admin()
            update_dict = {
                'ADid': admin.ADid
            }
            for key in att.keys():
                lower_key = str(key).lower()
                value = data.get(lower_key)
                if value or value == 0:
                    if key != 'ATTname' and not str(value).isdigit():
                            raise ParamsError('{} 只能是自然数'.format(getattr(ActivationType, key).comment))
                    update_dict.setdefault(key, value)
            att.update(update_dict)
            db.session.add(att)

            self.base_admin.create_action(AdminActionS.update.value, 'ActivationType', attid)
        return Success('修改成功', data=attid)

    def get_activationtype(self):
        data = parameter_required('attid')
        att = ActivationType.query.filter_by(ATTid=data.get('attid'), isdelete=False).first_('活跃度获取方式未被记录')
        return Success(data=att)

    def list_activationtype(self):
        att_list = ActivationType.query.filter_by(isdelete=False).order_by(ActivationType.updatetime.desc()).all_with_page()
        return Success(data=att_list)

    @token_required
    def get_duration_activation(self):
        data = parameter_required('tistarttime', 'tiendtime')
        if is_admin():
            usid = data.get('usid')
        elif common_user():
            usid = getattr(request, 'user').id
        else:
            raise AuthorityError('请登录')
        start = self._trans_time(data.get('tistarttime'))
        end = self._trans_time(data.get('tiendtime'))

        at_list = Activation.query.filter(
            Activation.USid == usid, Activation.createtime >= start, Activation.createtime <= end).all_with_page()
        for at in at_list:
            self._fill_at(at)

    def _trans_time(self, time):
        if isinstance(time, datetime):
            return time
        try:
            time = datetime.strptime(str(time), '%Y-%m-%d %H:%M:%S')
            return time
        except Exception as e:
            raise ParamsError('时间格式不正确')

    def _fill_at(self, at):
        att = ActivationType.query.filter_by(ATTid=at.ATTid, isdelet=False).first()
        if not att:
            return
        at.fill('attname', att.ATTname)
