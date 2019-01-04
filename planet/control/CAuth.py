from flask import request, make_response, jsonify

from planet.common.success_response import Success
from planet.common.token_handler import token_required, usid_to_token
from planet.models import User, Admin, Supplizer


class CAuth:
    @token_required
    def fresh(self):
        usid = request.user.id
        if request.user.model == 'User':
            user = User.query.filter(
                User.USid == usid,
                User.isdelete == False
            ).first_('用户已删除')
            jwt = usid_to_token(usid, model='User', level=user.USlevel, username=user.USname)
        elif request.user.model == 'Admin':
            admin = Admin.query.filter(
                Admin.ADid == request.user.id,
                Admin.isdelete == False,
                Admin.ADstatus == 0
            ).first_('管理员状态有误')
            jwt = usid_to_token(usid, model='Admin', level=admin.ADlevel, username=admin.ADname)
        else:
            supplizer = Supplizer.query.filter(
                Supplizer.isdelete == False,
                Supplizer.SUid == request.user.id,
                Supplizer.SUstatus == 0
            ).first_('供应商状态有误')
            jwt = usid_to_token(usid, model='Supplizer', username=supplizer.SUname)
        return Success(data=jwt)

    def cookie_test(self):
        print(request.cookies.get('token'))
        res = jsonify({
            'hello': 1
        })
        res.set_cookie('token', 'i am cookie')
        return res




