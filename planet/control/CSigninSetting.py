import uuid

from flask import request

from planet.common.base_service import get_session
from planet.common.error_response import AuthorityError, ParamsError
from planet.common.params_validates import parameter_required
from planet.common.success_response import Success
from planet.common.token_handler import token_required, is_admin
from planet.extensions.register_ext import db
from planet.extensions.validates.activty import SignIndelete
from planet.models import SignInAward


class CSigninSetting():
    @get_session
    @token_required
    def add_or_update(self):
        if not is_admin():
            raise AuthorityError()
        # data = SignInSetting().valid_data()
        # data =
        sia_list = request.json
        sia_in_list = []
        siaday_list = []
        for sia in sia_list:
            if not isinstance(sia, dict):
                continue
            if not sia.get('siaday') or not sia.get('sianum'):
                continue
            try:
                siaday = int(sia.get('siaday'))
                sianum = int(sia.get('sianum'))
            except:
                continue
            check_sia = SignInAward.query.filter_by(SIAday=siaday, isdelete=False).first()
            if check_sia:
                if sianum != check_sia.SIAnum:
                    check_sia.SIAnum = sianum
            else:
                sia_in = SignInAward.create({
                    'SIAid': str(uuid.uuid1()),
                    'SIAday': siaday,
                    'SIAnum': sianum
                })
                sia_in_list.append(sia_in)
            siaday_list.append(siaday)
        delete_sia_list = SignInAward.query.filter(
            SignInAward.SIAday.notin_(siaday_list), SignInAward.isdelete == False).all()
        for delete_sia in delete_sia_list:
            delete_sia.isdelete = True

        db.session.add_all(sia_in_list)
        return Success('签到设置成功')

    @get_session
    @token_required
    def delete(self):
        if not is_admin():
            raise AuthorityError()
        data = SignIndelete().valid_data()
        siaid = data.siaid.data
        check_sia = SignInAward.query.filter_by(SIAid=siaid, isdelete=False).delete_()
        if not check_sia:
            raise ParamsError('已删除')
        return Success('删除设置成功')

    @get_session
    @token_required
    def get_all(self):
        sia_list = SignInAward.query.filter_by(isdelete=False).order_by(SignInAward.SIAday).all()
        return Success('获取设置成功', data=sia_list)
