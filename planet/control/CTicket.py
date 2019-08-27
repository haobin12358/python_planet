# -*- coding: utf-8 -*-
import json
import uuid
import re
from datetime import datetime
from flask import current_app, request
from sqlalchemy import or_, false, extract, and_, func
from planet.common.error_response import ParamsError, TokenError
from planet.common.params_validates import parameter_required, validate_price, validate_arg
from planet.common.success_response import Success
from planet.common.token_handler import admin_required, is_admin, phone_required, common_user
from planet.config.enums import AdminActionS, TravelRecordType, TravelRecordStatus, MiniUserGrade, CollectionType, \
    EnterLogStatus, ApplyFrom, ApprovalAction, ApplyStatus, TicketStatus, TicketsOrderStatus
from planet.config.http_config import API_HOST
from planet.extensions.register_ext import db, mp_miniprogram
from planet.extensions.weixin.mp import WeixinMPError
from planet.models.ticket import Ticket, Linkage, TicketLinkage, TicketsOrder
from planet.models import EnterLog, Play, Approval
from planet.models.user import AddressArea, AddressCity, AddressProvince, Admin, User, UserCollectionLog
from planet.models.scenicspot import ScenicSpot, TravelRecord, Toilet, CustomizeShareContent
from planet.control.BaseControl import BASEADMIN, BaseController, BASEAPPROVAL
from planet.control.CPlay import CPlay
from planet.control.CUser import CUser


class CTicket(object):

    def __init__(self):
        self.BaseAdmin = BASEADMIN()
        self.cplay = CPlay()
        self.cuser = CUser()

    @admin_required
    def create_ticket(self):
        """创建票务"""
        data = request.json
        tistarttime, tiendtime, tiprice, tideposit, tinum, liids = self._validate_ticket_param(data)
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
                                    'TIcertificate': data.get('ticertificate'),
                                    'TIdetails': data.get('tidetails'),
                                    'TIprice': tiprice,
                                    'TIdeposit': tideposit,
                                    'TIstatus': TicketStatus.ready.value,
                                    'TInum': tinum,
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
        # todo 定时开始任务
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
                ticket.update({'isdelete': True})
                TicketLinkage.query.filter(TicketLinkage.isdelete == false(),
                                           TicketLinkage.TIid == ticket.TIid).delete_(synchronize_session=False)
                self.BaseAdmin.create_action(AdminActionS.delete.value, 'Ticket', ticket.TIid)
            elif ticket.TIstatus < TicketStatus.interrupt.value and data.get('interrupt'):
                ticket.update({'TIstatus': TicketStatus.interrupt.value})
                # todo 已有抢票产生时，中止活动，直接退钱？
            else:
                if ticket.TIstatus < TicketStatus.interrupt.value:
                    raise ParamsError('仅可修改已中止或已结束的活动')
                tistarttime, tiendtime, tiprice, tideposit, tinum, liids = self._validate_ticket_param(data)
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
                            'tiendtime': '抢票结束时间', 'tiprice': '票价', 'tideposit': '最低押金',
                            'tinum': '门票数量', 'tidetails': '详情'}, datafrom=data)
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
        return tistarttime, tiendtime, tiprice, tideposit, tinum, liids

    def get_ticket(self):
        """门票详情"""
        args = request.args.to_dict()
        tiid = args.get('tiid')
        tsoid = args.get('tsoid')
        if not (tiid or tsoid):
            raise ParamsError
        ticketorder = None
        if tsoid:
            ticketorder = TicketsOrder.query.filter(TicketsOrder.isdelete == false(),
                                                    TicketsOrder.TSOid == tsoid).first()
            tiid = ticketorder.TIid if ticketorder else tiid
        ticket = Ticket.query.filter(Ticket.isdelete == false(), Ticket.TIid == tiid).first()
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
        if ticketorder:
            ticket.fill('tsoid', ticketorder.TSOid)
            ticket.fill('tsocode', ticketorder.TSOcode)
            ticket.fill('tsostatus', ticketorder.TSOstatus)
            ticket.fill('tsostatus_zh', TicketsOrderStatus(ticketorder.TSOstatus).zh_value)

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
        [self._fill_ticket(x) for x in tickets]
        return Success(data=tickets)

    def _list_ticketorders(self):
        if not common_user():
            raise TokenError
        tos = TicketsOrder.query.filter(TicketsOrder.isdelete == false(),
                                        TicketsOrder.USid == getattr(request, 'user').id
                                        ).order_by(TicketsOrder.createtime.desc()).all_with_page()
        res = []
        for to in tos:
            ticket = Ticket.query.filter(Ticket.isdelete == false(), Ticket.TIid == to.TIid).first()
            self._fill_ticket(ticket, to)
            res.append(ticket)
        return Success(data=res)

    def list_linkage(self):
        """所有联动平台"""
        linkages = Linkage.query.filter(Linkage.isdelete == false()).all()
        return Success(data=linkages)

    @phone_required
    def order(self):
        """购买"""
        data = parameter_required(('tiid', 'number'))
        ticket = Ticket.query.filter(Ticket.isdelete == false(), Ticket.TIid == data.get('tiid')
                                     ).first_('未找到该门票信息')
        if ticket.TIstatus != TicketStatus.active.value:
            raise ParamsError('放票尚未开始')
        with db.auto_commit():
            TicketsOrder.create({'TSOid': str(uuid.uuid1()),
                                 'USid': getattr(request, 'user').id,
                                 'TIid': ticket.TIid,
                                 })
        pass

