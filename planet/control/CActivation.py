import uuid
from datetime import datetime

from flask import request, current_app
from sqlalchemy import false

from planet.common.error_response import ParamsError, AuthorityError, StatusError
from planet.common.params_validates import parameter_required
from planet.common.success_response import Success
from planet.common.token_handler import admin_required, get_current_admin, token_required, common_user, is_admin, \
    get_current_user
from planet.config.enums import AdminActionS, ActivationTypeType, ActivationTypeEnum
from planet.control.CTicket import CTicket
from planet.extensions.register_ext import db
from planet.models import ActivationType, Activation, UserLinkage, TicketsOrderActivation


class CActivation(CTicket):
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

            self.BaseAdmin.create_action(AdminActionS.update.value, 'ActivationType', attid)
        return Success('修改成功', data=attid)

    def get_activationtype(self):
        data = parameter_required('attid')
        att = ActivationType.query.filter_by(ATTid=data.get('attid'), isdelete=False).first_('活跃度获取方式未被记录')
        return Success(data=att)

    def list_activationtype(self):
        data = parameter_required()
        filter_args = {
            ActivationType.isdelete == false()
        }
        if data.get('atttype'):
            filter_args.add(ActivationType.ATTtype == data.get('atttype'))
        att_list = ActivationType.query.filter(*filter_args).order_by(ActivationType.updatetime.desc()).all_with_page()
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
            current_app.logger.info('时间格式不正确 time str {} error {}'.format(time, e))
            raise ParamsError('时间格式不正确')

    def _fill_at(self, at):
        att = ActivationType.query.filter_by(ATTid=at.ATTid, isdelet=False).first()
        if not att:
            return
        at.fill('attname', att.ATTname)

    @token_required
    def bind_linkage(self):
        data = parameter_required()
        userlinkages = data.get('userlinkages', [])
        user = get_current_user()
        with db.auto_commit():
            for ula in userlinkages:
                if not ula.get('ulaaccount'):
                    continue
                ula_instance = UserLinkage.query.filter_by(USid=user.USid, ATTid=ula.get('attid'),
                                                           isdelete=False).first()
                if ula_instance:
                    current_app.logger.info('已经绑定账号 {}'.format(ula_instance.ULAaccount))
                    if ula.get('ulaaccount') != ula_instance.ULAaccount:
                        current_app.logger.info('修改已经绑定账号为 {}'.format(ula.get('ulaaccount')))

                        if ula_instance.ULAaccount:
                            continue
                        ula_instance.ULAaccount = ula.get('ulaaccount')
                        db.session.add(ula_instance)
                else:
                    ula_instance = UserLinkage.create({
                        'ULAid': str(uuid.uuid1()),
                        'ATTid': ula.get('attid'),
                        'USid': user.USid,
                        'ULAaccount': ula.get('ulaaccount')
                    })
                    db.session.add(ula_instance)
                    current_app.logger.info('创建绑定账号 {}'.format(ula.get('ulaaccount')))
                self.Baseticket.add_activation(ula.get('attid'), user.USid, ula_instance.ULAid)
        return Success('绑定成功')

    @token_required
    def get_userlinkage(self):
        user = get_current_user()
        infoatt_list = ActivationType.query.filter_by(ATTtype=ActivationTypeType.info.value, isdelete=False).all()
        usid = user.USid
        for infoatt in infoatt_list:
            ula = UserLinkage.query.filter_by(USid=usid, ATTid=infoatt.ATTid, isdelete=False).first()
            ulaaccount = None
            if ula:
                ulaaccount = ula.ULAaccount
            infoatt.fill('ulaaccount', ulaaccount)
        return Success(data=infoatt_list)

    @admin_required
    def reward(self):
        data = parameter_required({'trid': '', 'atnum': '打赏数目'})
        admin = get_current_admin()

        with db.auto_commit():
            self._add_activation(data, ActivationTypeEnum.reward.value, admin.ADid)

        return Success('打赏成功')

    @admin_required
    def select(self):
        data = parameter_required('trid')
        select_at = TicketsOrderActivation.query.join(
            Activation, Activation.ATid == TicketsOrderActivation.ATid).filter(
            Activation.isdelete == false(),
            Activation.ATTid == ActivationTypeEnum.selected.value,
            TicketsOrderActivation.TOAcontent == data.get('trid'),
            TicketsOrderActivation.isdelete == false()).first()
        if select_at:
            raise StatusError('已经加精')

        with db.auto_commit():
            self._add_activation(data, ActivationTypeEnum.selected.value, data.get('trid'))

        return Success('精选成功')

    def _add_activation(self, data, attid, contentid):
        toa_list = TicketsOrderActivation.query.join(
            Activation, Activation.ATid == TicketsOrderActivation.ATid).filter(
            Activation.isdelete == false(),
            TicketsOrderActivation.isdelete == false(),
            TicketsOrderActivation.TOAcontent == data.get('trid'),
            Activation.ATTid == ActivationTypeEnum.publish.value,
        ).all()
        if not toa_list:
            raise StatusError('当前随笔没有加分到任何活动中')
        loop = 0
        for toa in toa_list:
            at = Activation.query.filter_by(ATid=toa.ATid, isdelete=False).first()

            # 添加 打赏奖励
            self.Baseticket.add_activation(attid, at.USid, contentid, data.get('atnum', 0), loop)
            loop += 1
