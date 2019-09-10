# -*- coding: utf-8 -*-
import json
import uuid
from datetime import datetime, timedelta
from flask import current_app, request
from sqlalchemy import false, func
from planet.extensions.tasks import start_ticket, end_ticket, celery
from planet.common.error_response import ParamsError, TokenError, StatusError
from planet.common.params_validates import parameter_required, validate_price, validate_arg
from planet.common.success_response import Success
from planet.common.token_handler import admin_required, is_admin, phone_required, common_user
from planet.common.playpicture import PlayPicture
from planet.config.enums import AdminActionS, TicketStatus, TicketsOrderStatus, PlayPayType, TicketDepositType, \
    PayType, UserMaterialFeedbackStatus, ActivationTypeEnum
from planet.extensions.register_ext import db, conn
from planet.config.secret import API_HOST
from planet.models.ticket import Ticket, Linkage, TicketLinkage, TicketsOrder, TicketDeposit, UserMaterialFeedback, \
    TicketRefundRecord, ActivationType, Activation
from planet.models.user import User, UserInvitation
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
        ticket_dict, liids = self._validate_ticket_param(data)
        if Ticket.query.filter(Ticket.isdelete == false(), Ticket.TIname == data.get('tiname')).first():
            raise ParamsError('该门票名称已存在')
        instance_list = []
        with db.auto_commit():
            ticket_dict.update({'TIid': str(uuid.uuid1()),
                                'ADid': getattr(request, 'user').id,
                                'TIname': data.get('tiname'),
                                'TIimg': data.get('tiimg'),
                                'TIrules': data.get('tirules'),
                                'TIcertificate': data.get('ticertificate') if data.get('ticertificate') else None,
                                'TIdetails': data.get('tidetails'),
                                'TIstatus': TicketStatus.ready.value,
                                'TIabbreviation': data.get('tiabbreviation'),
                                })
            ticket = Ticket.create(ticket_dict)
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
        # 异步任务: 开始
        self._create_celery_task(ticket.TIid, ticket_dict.get('TIstartTime'))
        # 异步任务: 结束
        self._create_celery_task(ticket.TIid, ticket_dict.get('TIendTime'), start=False)
        self.BaseAdmin.create_action(AdminActionS.insert.value, 'Ticket', ticket.TIid)
        return Success('创建成功', data={'tiid': ticket.TIid})

    @admin_required
    def update_ticket(self):
        """编辑门票"""
        data = parameter_required('tiid')
        ticket = Ticket.query.filter(Ticket.isdelete == false(),
                                     Ticket.TIid == data.get('tiid')).first_('未找到该票务信息')
        if Ticket.query.filter(Ticket.isdelete == false(), Ticket.TIname == data.get('tiname'),
                               Ticket.TIid != ticket.TIid, Ticket.TIstatus != TicketStatus.over.value).first():
            raise ParamsError('该门票名称已存在')
        instance_list = []
        with db.auto_commit():
            if data.get('delete'):
                if ticket.TIstatus == TicketStatus.active.value:
                    raise ParamsError('无法直接删除正在抢票中的活动')
                ticket.update({'isdelete': True})
                TicketLinkage.query.filter(TicketLinkage.isdelete == false(),
                                           TicketLinkage.TIid == ticket.TIid).delete_(synchronize_session=False)
                self._cancle_celery_task('start_ticket{}'.format(ticket.TIid))
                self._cancle_celery_task('end_ticket{}'.format(ticket.TIid))
                self.BaseAdmin.create_action(AdminActionS.delete.value, 'Ticket', ticket.TIid)
            elif data.get('interrupt'):
                if ticket.TIstatus > TicketStatus.active.value:
                    raise StatusError('该状态下无法中止')
                if ticket.TIstatus == TicketStatus.active.value:  # 抢票中的退押金
                    current_app.logger.info('interrupt active ticket')
                    ticket_orders = self._query_not_won(ticket.TIid)
                    total_row = 0
                    for to_info in ticket_orders:
                        row_count = self._deposit_refund(to_info)
                        total_row += row_count
                    current_app.logger.info('共退款{}条记录'.format(total_row))
                ticket.update({'TIstatus': TicketStatus.interrupt.value})
                self._cancle_celery_task('start_ticket{}'.format(ticket.TIid))
                self._cancle_celery_task('end_ticket{}'.format(ticket.TIid))
            else:
                if ticket.TIstatus < TicketStatus.interrupt.value:
                    raise ParamsError('仅可编辑已中止或已结束的活动')
                ticket_dict, liids = self._validate_ticket_param(data)
                ticket_dict.update({'TIname': data.get('tiname'),
                                    'TIimg': data.get('tiimg'),
                                    'TIrules': data.get('tirules'),
                                    'TIcertificate': data.get('ticertificate'),
                                    'TIdetails': data.get('tidetails'),
                                    'TIstatus': TicketStatus.ready.value,
                                    'TIabbreviation': data.get('tiabbreviation'),
                                    })
                if ticket.TIstatus == TicketStatus.interrupt.value:  # 中止的情况
                    current_app.logger.info('edit interrupt ticket')
                    ticket.update(ticket_dict)
                    TicketLinkage.query.filter(TicketLinkage.isdelete == false(),
                                               TicketLinkage.TIid == ticket.TIid).delete_()  # 删除原来的关联
                else:  # 已结束的情况，重新发起
                    current_app.logger.info('edit ended ticket')
                    ticket_dict.update({'TIid': str(uuid.uuid1())})
                    ticket = Ticket.create(ticket_dict)

                for liid in liids:
                    linkage = Linkage.query.filter(Linkage.isdelete == false(), Linkage.LIid == liid).first()
                    if not linkage:
                        continue
                    tl = TicketLinkage.create({'TLid': str(uuid.uuid1()),
                                               'LIid': liid,
                                               'TIid': ticket.TIid})
                    instance_list.append(tl)
                self._cancle_celery_task('start_ticket{}'.format(ticket.TIid))
                self._cancle_celery_task('end_ticket{}'.format(ticket.TIid))
                self._create_celery_task(ticket.TIid, ticket_dict.get('TIstartTime'))
                self._create_celery_task(ticket.TIid, ticket_dict.get('TIendTime'), start=False)
            instance_list.append(ticket)
            db.session.add_all(instance_list)
            self.BaseAdmin.create_action(AdminActionS.update.value, 'Ticket', ticket.TIid)
        return Success('编辑成功', data={'tiid': ticket.TIid})

    @staticmethod
    def _validate_ticket_param(data):
        parameter_required({'tiname': '票务名称', 'tiimg': '封面图', 'tistarttime': '抢票开始时间',
                            'tiendtime': '抢票结束时间', 'tirules': '规则', 'tiprice': '票价', 'tideposit': '最低押金',
                            'tinum': '门票数量', 'tidetails': '详情', 'tibanner': '详情轮播图'}, datafrom=data)
        tistarttime = validate_arg(r'^\d{4}(-\d{2}){2} \d{2}(:\d{2}){2}$', str(data.get('tistarttime')), '抢票开始时间格式错误')
        tiendtime = validate_arg(r'^\d{4}(-\d{2}){2} \d{2}(:\d{2}){2}$', str(data.get('tiendtime')), '抢票结束时间格式错误')
        tistarttime, tiendtime = map(lambda x: datetime.strptime(x, '%Y-%m-%d %H:%M:%S'), (tistarttime, tiendtime))
        now = datetime.now()
        if tistarttime < now:
            raise ParamsError('抢票开始时间应大于现在时间')
        if tiendtime <= tistarttime:
            raise ParamsError('抢票结束时间应大于开始时间')

        titripstarttime = validate_arg(r'^\d{4}(-\d{2}){2} \d{2}(:\d{2}){2}$', str(data.get('titripstarttime')),
                                       '游玩开始时间格式错误')
        titripendtime = validate_arg(r'^\d{4}(-\d{2}){2} \d{2}(:\d{2}){2}$', str(data.get('titripendtime')),
                                     '游玩结束时间格式错误')
        titripstarttime, titripendtime = map(lambda x: datetime.strptime(x, '%Y-%m-%d %H:%M:%S'),
                                             (titripstarttime, titripendtime))
        if titripstarttime < now:
            raise ParamsError('游玩开始时间应大于现在时间')
        if titripstarttime < tiendtime:
            raise ParamsError('游玩开始时间不能小于抢票结束时间')
        if titripendtime <= titripstarttime:
            raise ParamsError('游玩结束时间应大于开始时间')

        tiprice, tideposit = map(lambda x: validate_price(x, can_zero=False),
                                 (data.get('tiprice'), data.get('tideposit')))
        if tiprice < tideposit:
            raise ParamsError('最低押金不能大于票价')
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
        if not isinstance(data.get('tibanner'), list):
            raise ParamsError('tibanner 格式错误')
        tibanner = json.dumps(ticategory)

        ticket_dicket = {'TIstartTime': tistarttime,
                         'TIendTime': tiendtime,
                         'TItripStartTime': titripstarttime,
                         'TItripEndTime': titripendtime,
                         'TIprice': tiprice,
                         'TIdeposit': tideposit,
                         'TInum': tinum,
                         'TIcategory': ticategory,
                         'TIbanner': tibanner
                         }
        return ticket_dicket, liids

    def get_ticket(self):
        """门票详情"""
        args = request.args.to_dict()
        tiid = args.get('tiid')
        tsoid = args.get('tsoid')
        secret_usid = args.get('secret_usid')
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
        if secret_usid:
            try:
                superid = super(CTicket, self)._base_decode(secret_usid)
                current_app.logger.info('secret_usid --> superid {}'.format(superid))
                if common_user() and superid != getattr(request, 'user').id:
                    with db.auto_commit():
                        uin = UserInvitation.create({
                            'UINid': str(uuid.uuid1()),
                            'USInviter': superid,
                            'USInvited': getattr(request, 'user').id,
                            'UINapi': request.path
                        })
                        current_app.logger.info('已创建邀请记录')
                        db.session.add(uin)
            except Exception as e:
                current_app.logger.info('secret_usid 记录失败 error = {}'.format(e))

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
        # ticket.fill('residual', ticket.TInum)  # todo fake number ?
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
            ticket.fill('tsoqrcode',
                        ticketorder['TSOqrcode'] if ticketorder.TSOstatus > TicketsOrderStatus.has_won.value else None)
        umfstatus = -1 if not umf or umf.UMFstatus == UserMaterialFeedbackStatus.reject.value else umf.UMFstatus
        ticket.fill('umfstatus', umfstatus)  # 反馈素材审核状态
        ticket.fill('tirewardnum', tirewardnum)  # 中奖号码
        ticket.fill('residual_deposit', residual_deposit)  # 剩余押金
        ticket.fill('triptime', '{} - {}'.format(ticket.TItripStartTime.strftime("%Y/%m/%d"),
                                                 ticket.TItripEndTime.strftime("%Y/%m/%d")))
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
                                      ).order_by(Ticket.TIstatus.asc(), Ticket.createtime.asc()).all_with_page()
        for ticket in tickets:
            self._fill_ticket(ticket)
            ticket.fields = ['TIid', 'TIname', 'TIimg', 'TIstartTime', 'TIendTime', 'TIstatus', 'TIprice',
                             'interrupt', 'tistatus_zh', 'ticategory', 'TItripStartTime', 'TItripEndTime',
                             'TInum']
            # ticket.fill('short_str', '{}.{}抢票开启 | {}'.format(ticket.TIstartTime.month,
            #                                                  ticket.TIstartTime.day, ticket.TIabbreviation))
            ticket.fill('apply_num', db.session.query(func.count(TicketsOrder.TSOid)
                                                      ).filter(TicketsOrder.isdelete == false(),
                                                               TicketsOrder.TIid == ticket.TIid,
                                                               TicketsOrder.TSOstatus > TicketsOrderStatus.not_won.value
                                                               ).scalar() or 0)
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
                             'tsostatus', 'tsostatus_zh', 'interrupt', 'tistatus_zh', 'ticategory', 'tsoqrcode']
            # ticket.fill('short_str', '{}.{}抢票开启 | {}'.format(ticket.TIstartTime.month,
            #                                                  ticket.TIstartTime.day, ticket.TIabbreviation))
            res.append(ticket)
            del ticket
        return Success(data=res)

    def list_linkage(self):
        """所有联动平台"""
        linkages = Linkage.query.filter(Linkage.isdelete == false()).all()
        return Success(data=linkages)

    @admin_required
    def list_trade(self):
        """门票购买记录"""
        args = parameter_required('tiid')
        tiid = args.get('tiid')
        ticket = Ticket.query.filter(Ticket.isdelete == false(), Ticket.TIid == tiid).first_('无信息')
        tos = TicketsOrder.query.filter(TicketsOrder.isdelete == false(), TicketsOrder.TIid == tiid
                                        ).order_by(TicketsOrder.TSOstatus.desc(),
                                                   TicketsOrder.createtime.desc()).all_with_page()
        res = []
        for to in tos:
            usinfo = db.session.query(User.USname, User.USheader
                                      ).filter(User.isdelete == false(), User.USid == to.USid).first()
            if not usinfo:
                continue
            res.append({'usname': usinfo[0],
                        'usheader': usinfo[1],
                        'tsoid': to.TSOid,
                        'createtime': to.createtime,
                        'tsostatus': to.TSOstatus,
                        'tsostatus_zh': TicketsOrderStatus(to.TSOstatus).zh_value
                        })
        trade_num, award_num = map(lambda x: db.session.query(func.count(TicketsOrder.TSOid)
                                                              ).filter(TicketsOrder.isdelete == false(),
                                                                       TicketsOrder.TIid == tiid,
                                                                       TicketsOrder.TSOstatus == x,
                                                                       ).scalar() or 0,
                                   (TicketsOrderStatus.completed.value, TicketsOrderStatus.has_won.value))
        ticket_info = {'tiid': ticket.TIid,
                       'tiname': ticket.TIname,
                       'time': '{} - {}'.format(ticket.TIstartTime, ticket.TIendTime),
                       'tistatus': ticket.TIstatus,
                       'tistatus_zh': TicketStatus(ticket.TIstatus).zh_value,
                       'trade_num': '{} / {}'.format(trade_num, ticket.TInum),
                       'award_num': '{} / {}'.format(award_num, ticket.TInum)}
        return Success(data={'ticket': ticket_info,
                             'ticketorder': res}
                       )

    @admin_required
    def set_award(self):
        """设置中奖"""
        data = parameter_required('tsoid')
        tsoid = data.get('tsoid')
        ticket_order = TicketsOrder.query.filter(TicketsOrder.isdelete == false(),
                                                 TicketsOrder.TSOid == tsoid,
                                                 TicketsOrder.TSOstatus == TicketsOrderStatus.pending.value
                                                 ).first_('状态错误')
        ticket = Ticket.query.filter(Ticket.isdelete == false(), Ticket.TIid == ticket_order.TIid).first()
        if not ticket or ticket.TIstatus != TicketStatus.over.value:
            raise ParamsError('抢票尚未结束')
        award_num = self._query_award_num(ticket.TIid)
        current_app.logger.info('已中奖数：{} / {}'.format(award_num, ticket.TInum))
        if award_num >= ticket.TInum:
            raise StatusError('已达最大发放票数')
        with db.auto_commit():
            update_dict = {'TSOqrcode': 'https://play.bigxingxing.com/img/qrcode/2019/9/3/QRCODE.png',
                           'TSOstatus': TicketsOrderStatus.has_won.value}
            if ticket.TIdeposit == ticket.TIprice:  # 第二次支付押金0元的情况
                update_dict['TSOstatus'] = TicketsOrderStatus.completed.value
            ticket_order.update(update_dict)
            db.session.add(ticket_order)
            db.session.flush()
            awarded_num = self._query_award_num(ticket.TIid)
            current_app.logger.info('设置后中奖数：{} / {}'.format(awarded_num, ticket.TInum))
            if awarded_num == ticket.TInum:  # 未中奖退钱
                other_to = self._query_not_won(ticket.TIid)
                total_row_count = 0
                for oto in other_to:
                    row_count = self._deposit_refund(oto)
                    total_row_count += row_count
                current_app.logger.info('共{}条未中奖'.format(total_row_count))
        return Success('设置成功', data=tsoid)

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

    @staticmethod
    def _query_award_num(tiid):
        return db.session.query(func.count(TicketsOrder.TSOid)
                                ).filter(TicketsOrder.isdelete == false(),
                                         TicketsOrder.TIid == tiid,
                                         TicketsOrder.TSOstatus == TicketsOrderStatus.has_won.value
                                         ).scalar() or 0

    @staticmethod
    def _query_not_won(tiid):
        return db.session.query(TicketsOrder.USid, TicketsOrder.TIid,
                                func.group_concat(TicketsOrder.TSOid)
                                ).filter(TicketsOrder.isdelete == false(),
                                         TicketsOrder.TIid == tiid,
                                         TicketsOrder.TSOstatus == TicketsOrderStatus.pending.value
                                         ).group_by(TicketsOrder.USid).all()

    @staticmethod
    def _create_celery_task(tiid, starttime, start=True):
        if start:
            task_id = start_ticket.apply_async(args=(tiid,), eta=starttime - timedelta(hours=8))
            connid = 'start_ticket{}'.format(tiid)
        else:
            connid = 'end_ticket{}'.format(tiid)
            task_id = end_ticket.apply_async(args=(tiid,), eta=starttime - timedelta(hours=8))
        current_app.logger.info('ticket async task | connid: {}, task_id: {}'.format(connid, task_id))
        conn.set(connid, task_id)

    @staticmethod
    def _cancle_celery_task(conid):
        exist_task_id = conn.get(conid)
        if exist_task_id:
            exist_task_id = str(exist_task_id, encoding='utf-8')
            current_app.logger.info('已有任务id: {}'.format(exist_task_id))
            celery.AsyncResult(exist_task_id).revoke()
            conn.delete(conid)

    def _deposit_refund(self, to_info):
        usid, tiid, tsoids = to_info
        tsoids = tsoids.split(',')
        current_app.logger.info('deposit refund, TSOids:{}'.format(tsoids))
        td_info = db.session.query(TicketDeposit.OPayno, func.sum(TicketDeposit.TDdeposit)
                                   ).filter(TicketDeposit.isdelete == false(),
                                            TicketDeposit.TSOid.in_(tsoids)).group_by(TicketDeposit.OPayno).all()
        current_app.logger.info('td_info:{}'.format(td_info))
        for td in td_info:
            opayno, return_price = td
            current_app.logger.info('found refund opayno: {}, mount:{}'.format(opayno, return_price))
            mount_price = db.session.query(func.sum(TicketDeposit.TDdeposit)).filter(
                TicketDeposit.isdelete == false(),
                TicketDeposit.OPayno == opayno).scalar()
            current_app.logger.info('refund mount: {}; total deposit:{}'.format(return_price, mount_price))
            current_app.logger.info('refund usid: {}'.format(usid))

            if API_HOST != 'https://www.bigxingxing.com':
                mount_price = 0.01
                return_price = 0.01
            trr = TicketRefundRecord.create({'TRRid': str(uuid.uuid1()),
                                             'USid': usid,
                                             'TRRredund': return_price,
                                             'TRRtotal': mount_price,
                                             'OPayno': opayno})
            db.session.add(trr)
            try:
                super(CTicket, self)._refund_to_user(
                    out_trade_no=opayno,
                    out_request_no=trr.TRRid,
                    mount=return_price,
                    old_total_fee=mount_price
                )
            except Exception as e:
                raise StatusError('微信商户平台：{}'.format(e))

        row_count = TicketsOrder.query.filter(TicketsOrder.isdelete == false(),
                                              TicketsOrder.TSOid.in_(tsoids)
                                              ).update({'TSOstatus': TicketsOrderStatus.not_won.value},
                                                       synchronize_session=False)
        current_app.logger.info('change status to not won, count: {}'.format(row_count))
        return row_count

    @phone_required
    def get_promotion(self):
        data = parameter_required('tiid')
        user = User.query.filter(User.isdelete == false(), User.USid == getattr(request, 'user').id).first_('请重新登录')
        tiid = data.get('tiid')
        params = data.get('params')
        # play = Play.query.filter_by(PLid=plid, isdelete=False).first()
        ticket = Ticket.query.filter(
            Ticket.TIid == tiid, Ticket.TIstatus < TicketStatus.interrupt.value,
            Ticket.isdelete == false()).first_('活动已结束')

        usid = user.USid

        starttime = super(CTicket, self)._check_time(ticket.TItripStartTime)
        endtime = super(CTicket, self)._check_time(ticket.TItripEndTime, fmt='%m/%d')

        # 获取微信二维码
        from planet.control.CUser import CUser
        cuser = CUser()
        if 'secret_usid' not in params:
            params = '{}&secret_usid={}'.format(params, cuser._base_encode(usid))
        params_key = cuser.shorten_parameters(params, usid, 'params')
        wxacode_path = cuser.wxacode_unlimit(
            usid, {'params': params_key}, img_name='{}{}'.format(usid, tiid), )
        local_path, promotion_path = PlayPicture().create_ticket(
            ticket.TIimg, ticket.TIname, starttime, endtime, str(0), usid, tiid, wxacode_path)
        from planet.extensions.qiniu.storage import QiniuStorage
        qiniu = QiniuStorage(current_app)
        if API_HOST == 'https://www.bigxingxing.com':
            try:
                qiniu.save(local_path, filename=promotion_path[1:])
            except Exception as e:
                current_app.logger.info('上传七牛云失败，{}'.format(e.args))
        scene = cuser.dict_to_query_str({'params': params_key})
        current_app.logger.info('get scene = {}'.format(scene))
        return Success(data={
            'promotion_path': promotion_path,
            'scene': scene
        })

    def add_activation(self, attid, usid, atnum=0):
        att = ActivationType.query.filter_by(ATTid=attid).first()
        if not att:
            return
        if str(attid) != ActivationTypeEnum.reward.value:
            atnum = att.ATTnum

        atnum = int(atnum)

        db.session.add(Activation.create({
            'ATid': str(uuid.uuid1()),
            'USId': usid,
            'ATTid': attid,
            'ATnum': atnum
        }))
        now = datetime.now()

        tso_list = TicketsOrder.query.join(Ticket, Ticket.TIid == TicketsOrder.TIid).filter(
            TicketsOrder.TSOstatus == TicketsOrderStatus.pending.value,
            Ticket.TIstartTime <= now,
            Ticket.TIendTime >= now,
            Ticket.isdelete == false(),
            TicketsOrder.isdelete == false()).all()
        for tso in tso_list:
            tso.TSOactivation += atnum
