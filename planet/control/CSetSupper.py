# -*- coding: utf-8 -*-
import uuid
from planet.extensions.register_ext import db
from planet.models import User,UserInvitation
from planet.common.params_validates import parameter_required
from planet.common.success_response import Success


class CSetSupper():
    def test(self):
        data = parameter_required(('ustelphone1', 'ustelphone2'))
        a =data.get('ustelphone1')
        b =data.get('ustelphone2')
        add0 = User.query.filter(User.UStelphone == a,User.isdelete ==0).order_by(User.updatetime.desc()).first()
        c=add0.USid
        add1 = User.query.filter(User.UStelphone == b,User.isdelete ==0).order_by(User.updatetime.desc()).first()
        d=add1.USid,add1.USsupper1

        if d[1] == None:
            add1.USsupper1 = c[0]
            uin = UserInvitation.create({
                'UINid': str(uuid.uuid1()), 'USInviter': c[0], 'USInvited': d[0]})
            db.session.add(uin)
            db.session.commit()
            return Success("邀请成功")

        else:
            def check(x, y):
                z = UserInvitation.query.filter(
                    UserInvitation.USInvited == x, UserInvitation.USInviter == y,UserInvitation.isdelete==0).first()
                return z

            a = check(d[0], d[1])

            if a == None:
                add1.USsupper1 = c[0]
                uin = UserInvitation.create({
                    'UINid': str(uuid.uuid1()), 'USInviter': c[0], 'USInvited': d[0]})
                db.session.add(uin)
                db.session.commit()
                return Success("邀请人非法,修改成功")
            else:
                return Success('邀请人存在并合法')
