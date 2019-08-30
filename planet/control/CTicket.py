# -*- coding: utf-8 -*-
import json
import uuid
from datetime import datetime, timedelta
from flask import current_app, request
from sqlalchemy import false
from planet.extensions.tasks import start_ticket, celery
from planet.common.error_response import ParamsError, TokenError, StatusError
from planet.common.params_validates import parameter_required, validate_price, validate_arg
from planet.common.success_response import Success
from planet.common.token_handler import admin_required, is_admin, phone_required, common_user
from planet.config.enums import AdminActionS, TicketStatus, TicketsOrderStatus, PlayPayType, TicketDepositType, PayType, \
    UserMaterialFeedbackStatus
from planet.extensions.register_ext import db, conn
from planet.models.ticket import Ticket, Linkage, TicketLinkage, TicketsOrder, TicketDeposit, UserMaterialFeedback
from planet.models.user import User
from planet.control.BaseControl import BASEADMIN
from planet.control.CPlay import CPlay


class CTicket(CPlay):

    def __init__(self):
        super(CTicket, self).__init__()
        self.BaseAdmin = BASEADMIN()

    @admin_required
    def create_ticket(self):
        """创建票务"""
        data = request.json
        tistarttime, tiendtime, tiprice, tideposit, tinum, liids, ticategory = self._validate_ticket_param(data)
        if Ticket.query.filter(Ticket.isdelete == false(), Ticket.TIname == data.get('tiname')).first():
            raise ParamsError('该门票名称已存在')
        instance_list = []
        with db.auto_commit():
            ticket = Ticket.create({'TIid': str(uuid.uuid1()),
                                    'ADid': getattr(request, 'user').id,
                                    'TIname': data.get('tiname'),
                                    'TIimg': data.get('tiimg'),
                                    'TIstartTime': tistarttime,
                                    'TIendTime': tiendtime,
                                    'TIrules': data.get('tirules'),
                                    'TIcertificate': data.get('ticertificate') if data.get('ticertificate') else None,
                                    'TIdetails': data.get('tidetails'),
                                    'TIprice': tiprice,
                                    'TIdeposit': tideposit,
                                    'TIstatus': TicketStatus.ready.value,
                                    'TInum': tinum,
                                    'TIabbreviation': data.get('tiabbreviation'),
                                    'TIcategory': ticategory
                                    })
            instance_list.append(ticket)
            for liid in liids:
                linkage = Linkage.query.filter(Linkage.isdelete == false(), Linkage.LIid == liid).first()
                if not linkage:
                    continue
                tl = TicketLinkage.create({'TLid': str(uuid.uuid1()),
                                           'LIid': liid,
                                           'TIid': ticket.TIid})
                instance_list.append(tl)
            db.session.add_all(instance_list)
        # 定时开始任务
        start_task_id = start_ticket.apply_async(args=(ticket.TIid,), eta=tistarttime - timedelta(hours=8))
        # conn.set('start_ticket{}'.format(start_task_id), start_task_id)
        self.BaseAdmin.create_action(AdminActionS.insert.value, 'Ticket', ticket.TIid)
        return Success('创建成功', data={'tiid': ticket.TIid})

    @admin_required
    def update_ticket(self):
        """编辑门票"""
        data = parameter_required('tiid')
        ticket = Ticket.query.filter(Ticket.isdelete == false(),
                                     Ticket.TIid == data.get('tiid')).first_('未找到该票务信息')
        if Ticket.query.filter(Ticket.isdelete == false(), Ticket.TIname == data.get('tiname'),
                               Ticket.TIid != ticket.TIid).first():
            raise ParamsError('该门票名称已存在')
        isinstance_list = []
        with db.auto_commit():
            if data.get('delete'):
                if ticket.TIstatus == TicketStatus.active.value:
                    raise ParamsError('无法直接删除正在抢票中的活动')
                ticket.update({'isdelete': True})
                TicketLinkage.query.filter(TicketLinkage.isdelete == false(),
                                           TicketLinkage.TIid == ticket.TIid).delete_(synchronize_session=False)
                self.BaseAdmin.create_action(AdminActionS.delete.value, 'Ticket', ticket.TIid)
            elif data.get('interrupt'):
                if ticket.TIstatus > TicketStatus.active.value:
                    raise StatusError('该状态下无法中止')
                ticket.update({'TIstatus': TicketStatus.interrupt.value})
                # todo 已有抢票产生时，中止活动，直接退钱？
            else:
                if ticket.TIstatus < TicketStatus.interrupt.value:
                    raise ParamsError('仅可修改已中止或已结束的活动')
                # todo 编辑已结束的活动，影响已完成的显示，考虑是否重新创建
                tistarttime, tiendtime, tiprice, tideposit, tinum, liids, ticategory = self._validate_ticket_param(data)
                ticket.update({'TIname': data.get('tiname'),
                               'TIimg': data.get('tiimg'),
                               'TIstartTime': tistarttime,
                               'TIendTime': tiendtime,
                               'TIrules': data.get('tirules'),
                               'TIcertificate': data.get('ticertificate'),
                               'TIdetails': data.get('tidetails'),
                               'TIprice': tiprice,
                               'TIdeposit': tideposit,
                               'TIstatus': TicketStatus.ready.value,
                               'TInum': tinum,
                               'TIabbreviation': data.get('tiabbreviation'),
                               'TIcategory': ticategory
                               })
                TicketLinkage.query.filter(TicketLinkage.isdelete == false(),
                                           TicketLinkage.TIid == ticket.TIid).delete_()  # 删除原来的关联
                for liid in liids:
                    linkage = Linkage.query.filter(Linkage.isdelete == false(), Linkage.LIid == liid).first()
                    if not linkage:
                        continue
                    tl = TicketLinkage.create({'TLid': str(uuid.uuid1()),
                                               'LIid': liid,
                                               'TIid': ticket.TIid})
                    isinstance_list.append(tl)
            isinstance_list.append(ticket)
            db.session.add_all(isinstance_list)
            # todo 定时开始任务
            self.BaseAdmin.create_action(AdminActionS.update.value, 'Ticket', ticket.TIid)
        return Success('编辑成功', data={'tiid': ticket.TIid})

    @staticmethod
    def _validate_ticket_param(data):
        parameter_required({'tiname': '票务名称', 'tiimg': '封面图', 'tistarttime': '抢票开始时间',
                            'tiendtime': '抢票结束时间', 'tirules': '规则', 'tiprice': '票价', 'tideposit': '最低押金',
                            'tinum': '门票数量', 'tidetails': '详情', 'tiabbreviation': '列表页活动类型简称',
                            'ticategory': '列表页活动类型标签'}, datafrom=data)
        tistarttime = validate_arg(r'^\d{4}(-\d{2}){2} \d{2}(:\d{2}){2}$', data.get('tistarttime'), '抢票开始时间格式错误')
        tiendtime = validate_arg(r'^\d{4}(-\d{2}){2} \d{2}(:\d{2}){2}$', data.get('tiendtime'), '抢票结束时间格式错误')
        tistarttime, tiendtime = map(lambda x: datetime.strptime(x, '%Y-%m-%d %H:%M:%S'), (tistarttime, tiendtime))
        now = datetime.now()
        if tistarttime < now:
            raise ParamsError('抢票开始时间应大于现在时间')
        if tiendtime < tistarttime:
            raise ParamsError('抢票结束时间应大于开始时间')
        tiprice, tideposit = map(lambda x: validate_price(x, can_zero=False),
                                 (data.get('tiprice'), data.get('tideposit')))
        if tiprice < tideposit:
            raise ParamsError('最低押金应小于票价')
        tinum = data.get('tinum')
        if not isinstance(tinum, int) or int(tinum) <= 0:
            raise ParamsError('请输入合理的门票数量')
        liids = data.get('liids', [])
        if not isinstance(liids, list):
            raise ParamsError('liids 格式错误')
        ticategory = data.get('ticategory', [])
        if not isinstance(ticategory, list):
            raise ParamsError('ticategory 格式错误')
        ticategory = json.dumps(ticategory)
        return tistarttime, tiendtime, tiprice, tideposit, tinum, liids, ticategory

    def get_ticket(self):
        """门票详情"""
        args = request.args.to_dict()
        tiid = args.get('tiid')
        tsoid = args.get('tsoid')
        if not (tiid or tsoid):
            raise ParamsError
        ticketorder = None
        if tsoid:
            if not common_user():
                raise TokenError
            ticketorder = TicketsOrder.query.filter(TicketsOrder.isdelete == false(),
                                                    TicketsOrder.USid == getattr(request, 'user').id,
                                                    TicketsOrder.TSOid == tsoid).first()
            tiid = ticketorder.TIid if ticketorder else tiid
        ticket = Ticket.query.filter(Ticket.isdelete == false(), Ticket.TIid == tiid).first_('未找到该门票信息')
        self._fill_ticket(ticket, ticketorder=ticketorder)
        return Success(data=ticket)

    @staticmethod
    def _fill_ticket(ticket, ticketorder=None):
        ticket.hide('ADid')
        now = datetime.now()
        if ticket.TIstatus == TicketStatus.ready.value and ticket.TIstartTime > now:  # 距抢票开始倒计时
            countdown = ticket.TIstartTime - now
        elif ticket.TIstatus == TicketStatus.active.value and ticket.TIendTime > now:  # 距抢票结束倒计时
            countdown = ticket.TIendTime - now
        else:
            countdown = None
        if countdown:
            hours = str(countdown.days * 24 + (countdown.seconds // 3600))
            minutes = str((countdown.seconds % 3600) // 60)
            seconds = str((countdown.seconds % 3600) % 60)
            countdown = "{}:{}:{}".format('0' + hours if len(hours) == 1 else hours,
                                          '0' + minutes if len(minutes) == 1 else minutes,
                                          '0' + seconds if len(seconds) == 1 else seconds)

        ticket.fill('countdown', countdown)
        ticket.fill('tistatus_zh', TicketStatus(ticket.TIstatus).zh_value)
        ticket.fill('residual', ticket.TInum)  # todo fake number ?
        ticket.fill('interrupt', False if ticket.TIstatus < TicketStatus.interrupt.value else True)  # 是否中止
        ticket.fill('ticategory', json.loads(ticket.TIcategory))
        tirewardnum, residual_deposit, umf = None, None, None
        if ticketorder:
            ticket.fill('tsoid', ticketorder.TSOid)
            ticket.fill('tsocode', ticketorder.TSOcode)
            ticket.fill('tsostatus', ticketorder.TSOstatus)
            ticket.fill('tsostatus_zh', TicketsOrderStatus(ticketorder.TSOstatus).zh_value)
            if ticket.TIstatus == TicketStatus.over.value:
                tirewardnum = json.loads(ticket.TIrewardnum) if ticket.TIrewardnum else None
            if ticketorder.TSOstatus == TicketsOrderStatus.has_won.value:
                residual_deposit = ticket.TIprice - ticket.TIdeposit
            umf = UserMaterialFeedback.query.filter(UserMaterialFeedback.isdelete == false(),
                                                    UserMaterialFeedback.USid == getattr(request, 'user').id,
                                                    UserMaterialFeedback.TIid == ticket.TIid,
                                                    UserMaterialFeedback.TSOid == ticketorder.TSOid,
                                                    ).order_by(UserMaterialFeedback.createtime.desc()).first()
        umfstatus = -1 if not umf or umf.UMFstatus == UserMaterialFeedbackStatus.reject.value else umf.UMFstatus
        ticket.fill('umfstatus', umfstatus)  # 反馈素材审核状态
        ticket.fill('tirewardnum', tirewardnum)  # 中奖号码
        ticket.fill('residual_deposit', residual_deposit)  # 剩余押金
        if is_admin():
            linkage = Linkage.query.join(TicketLinkage, TicketLinkage.LIid == Linkage.LIid
                                         ).filter(Linkage.isdelete == false(),
                                                  TicketLinkage.isdelete == false(),
                                                  TicketLinkage.TIid == ticket.TIid).all()
            ticket.fill('linkage', linkage)

    def list_ticket(self):
        """门票列表"""
        args = request.args.to_dict()
        option = args.get('option')
        if option == 'my':  # 我的门票
            return self._list_ticketorders()
        filter_args = []
        if not is_admin():
            filter_args.append(Ticket.TIstatus < TicketStatus.interrupt.value)
        tickets = Ticket.query.filter(Ticket.isdelete == false(), *filter_args
                                      ).order_by(Ticket.TIstatus.desc(), Ticket.createtime.asc()).all_with_page()
        for ticket in tickets:
            self._fill_ticket(ticket)
            ticket.fields = ['TIid', 'TIname', 'TIimg', 'TIstartTime', 'TIendTime', 'TIstatus',
                             'interrupt', 'tistatus_zh', 'ticategory']
            ticket.fill('short_str', '{}.{}抢票开启 | {}'.format(ticket.TIstartTime.month,
                                                             ticket.TIstartTime.day, ticket.TIabbreviation))
        return Success(data=tickets)

    def _list_ticketorders(self):
        import copy
        if not common_user():
            raise TokenError
        tos = TicketsOrder.query.filter(TicketsOrder.isdelete == false(),
                                        TicketsOrder.USid == getattr(request, 'user').id
                                        ).order_by(TicketsOrder.createtime.desc()).all_with_page()
        res = []
        for to in tos:
            ticket = Ticket.query.filter(Ticket.isdelete == false(), Ticket.TIid == to.TIid).first()
            ticket = copy.deepcopy(ticket)
            if not ticket:
                current_app.logger.error('未找到ticket, tiid: {}'.format(to.TIid))
                continue
            self._fill_ticket(ticket, to)
            ticket.fields = ['TIid', 'TIname', 'TIimg', 'TIstartTime', 'TIendTime', 'TIstatus', 'tsoid', 'tsocode',
                             'tsostatus', 'tsostatus_zh', 'interrupt', 'tistatus_zh', 'ticategory']
            ticket.fill('short_str', '{}.{}抢票开启 | {}'.format(ticket.TIstartTime.month,
                                                             ticket.TIstartTime.day, ticket.TIabbreviation))
            res.append(ticket)
            del ticket
        return Success(data=res)

    def list_linkage(self):
        """所有联动平台"""
        linkages = Linkage.query.filter(Linkage.isdelete == false()).all()
        return Success(data=linkages)

    @phone_required
    def pay(self):
        """购买"""
        data = parameter_required()
        tiid, tsoid, numbers = data.get('tiid'), data.get('tsoid'), data.get('num')
        user = User.query.filter(User.isdelete == false(), User.USid == getattr(request, 'user').id).first_('请重新登录')
        opayno = super(CTicket, self)._opayno()
        instance_list, tscode_list = [], []
        with db.auto_commit():
            if tiid and numbers:  # 抢票
                ticket, mount_price, instance_list, tscode_list = self._grap_ticket_order(tiid, numbers, user, opayno,
                                                                                          instance_list, tscode_list)
            elif tsoid:  # 中奖后补押金
                ticket, mount_price, instance_list, tscode_list = self._patch_ticket_order(tsoid, user, opayno,
                                                                                           instance_list, tscode_list)
            else:
                raise ParamsError

            db.session.add_all(instance_list)
        body = ticket.TIname[:16] + '...'
        openid = user.USopenid1
        pay_args = super(CTicket, self)._add_pay_detail(opayno=opayno, body=body, PPpayMount=mount_price, openid=openid,
                                                        PPcontent=ticket.TIid,
                                                        PPpayType=PlayPayType.ticket.value)
        response = {
            'pay_type': PayType.wechat_pay.name,
            'opaytype': PayType.wechat_pay.value,
            'tscode': tscode_list,
            'args': pay_args
        }
        current_app.logger.info('response = {}'.format(response))
        return Success(data=response)

    def _grap_ticket_order(self, tiid, numbers, user, opayno, instance_list, tscode_list):
        if not (isinstance(numbers, int) and 0 < numbers < 11):
            raise ParamsError('数量错误, 单次可购票数 (1-10)')
        ticket = Ticket.query.filter(Ticket.isdelete == false(), Ticket.TIid == tiid
                                     ).first_('未找到该门票信息')
        if ticket.TIstatus != TicketStatus.active.value:
            raise ParamsError('活动尚未开始')
        last_trade = TicketsOrder.query.filter(TicketsOrder.TIid == tiid,
                                               TicketsOrder.USid == user.USid,
                                               TicketsOrder.TSOstatus == TicketsOrderStatus.pending.value
                                               ).order_by(TicketsOrder.createtime.desc()).first()
        if last_trade:
            current_app.logger.info('last trade time: {}'.format(last_trade.createtime))
            delta_time = datetime.now() - last_trade.createtime
            current_app.logger.info('delta time: {}'.format(delta_time))
            if delta_time.seconds < 6:
                raise ParamsError('正在努力排队中, 请稍后尝试重新提交')
        mount_price = ticket.TIdeposit * numbers
        last_tscode = db.session.query(TicketsOrder.TSOcode).filter(
            TicketsOrder.isdelete == false(),
            TicketsOrder.TIid == tiid,
            TicketsOrder.TSOstatus == TicketsOrderStatus.pending.value
        ).order_by(TicketsOrder.TSOcode.desc(),
                   TicketsOrder.createtime.desc(),
                   origin=True).first() or 0
        if last_tscode:
            last_tscode = last_tscode[0]
        current_app.logger.info('last tscode: {}'.format(last_tscode))
        for i in range(numbers):
            last_tscode += 1
            tscode = last_tscode
            tscode_list.append(tscode)
            current_app.logger.info('tscode: {}'.format(tscode))
            ticket_order = self._creat_ticket_order(user.USid, tiid, tscode)
            ticket_deposit = self._creat_ticket_deposit(ticket_order.TSOid, TicketDepositType.grab.value,
                                                        ticket.TIdeposit, opayno)
            instance_list.append(ticket_deposit)
            instance_list.append(ticket_order)
        return ticket, mount_price, instance_list, tscode_list

    def _patch_ticket_order(self, tsoid, user, opayno, instance_list, tscode_list):
        tso = TicketsOrder.query.filter(TicketsOrder.isdelete == false(), TicketsOrder.TSOid == tsoid,
                                        TicketsOrder.USid == user.USid).first_('未找到该信息')
        if tso.TSOstatus != TicketsOrderStatus.has_won.value:
            raise StatusError('支付条件未满足')
        ticket = Ticket.query.filter(Ticket.isdelete == false(), Ticket.TIid == tso.TIid
                                     ).first_('未找到该门票信息')
        mount_price = ticket.TIprice - ticket.TIdeposit
        ticket_deposit = self._creat_ticket_deposit(tsoid, TicketDepositType.patch.value, mount_price, opayno)
        instance_list.append(ticket_deposit)
        tscode_list.append(tso.TSOcode)
        return ticket, mount_price, instance_list, tscode_list

    @staticmethod
    def _creat_ticket_deposit(tsoid, tdtype, mount, opayno):
        return TicketDeposit.create({'TDid': str(uuid.uuid1()),
                                     'TSOid': tsoid,
                                     'TDdeposit': mount,
                                     'TDtype': tdtype,
                                     'OPayno': opayno})

    @staticmethod
    def _creat_ticket_order(usid, tiid, tscode):
        return TicketsOrder.create({'TSOid': str(uuid.uuid1()),
                                    'USid': usid,
                                    'TIid': tiid,
                                    'TSOcode': tscode,
                                    'isdelete': True})

    def _cancle_celery(self, conid):
        exist_task_id = conn.get(conid)
        if exist_task_id:
            exist_task_id = str(exist_task_id, encoding='utf-8')
            current_app.logger.info('已有任务id: {}'.format(exist_task_id))
            celery.AsyncResult(exist_task_id).revoke()
            conn.delete(conid)
