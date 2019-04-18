# -*- coding: utf-8 -*-
import uuid
from planet.extensions.register_ext import db
from planet.models import User, UserInvitation
from planet.common.params_validates import parameter_required
from planet.common.success_response import Success


class CSetSupper():
    def test(self):
        data = parameter_required(('ustelphone1', 'ustelphone2'))
        inviter = data.get('ustelphone1')
        invited = data.get('ustelphone2')
        add0 = User.query.filter(User.UStelphone == inviter, User.isdelete == False).order_by(
            User.updatetime.desc()).first()
        add1 = User.query.filter(User.UStelphone == invited, User.isdelete == False).order_by(
            User.updatetime.desc()).first()

        if add0 != None:
            c = add0.USid
            d = add1.USid, add1.USsupper1
            if d[1] == None:
                add1.USsupper1 = c
                uin = UserInvitation.create({
                    'UINid': str(uuid.uuid1()), 'USInviter': c, 'USInvited': d[0]})
                db.session.add(uin)
                db.session.commit()
                return Success("邀请成功")
            else:
                a = UserInvitation.query.filter(
                    UserInvitation.USInvited == d[0], UserInvitation.USInviter == d[1],
                    UserInvitation.isdelete == False).first()
                if a == None:
                    uin = UserInvitation.create({
                        'UINid': str(uuid.uuid1()), 'USInviter': d[1], 'USInvited': d[0]})
                    db.session.add(uin)
                    db.session.commit()
                    return Success("邀请人非法,修改成功")
                else:
                    return Success('邀请人已存在')
        else:
            return Success('邀请人不存在')
        ##使用一个session 多个事务的操作来完成。 这个不是很懂
