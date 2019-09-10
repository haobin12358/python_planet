import re
import uuid
import math
from datetime import datetime
from decimal import Decimal
from flask import current_app, request
from sqlalchemy import false, extract, or_, func
from planet.common.params_validates import parameter_required, validate_arg
from planet.common.success_response import Success
from planet.common.token_handler import phone_required
from planet.common.error_response import ParamsError
from planet.config.enums import EnterLogStatus, ApplyFrom, ApprovalAction, GuideApplyStatus, MakeOverStatus, PlayPayType
from planet.control.BaseControl import BASEAPPROVAL
from planet.extensions.register_ext import db
from planet.extensions.tasks import auto_agree_task
from planet.models.scenicspot import Guide
from planet.models.user import User, UserWallet, CashNotes, CoveredCertifiedNameLog
from planet.models.join import EnterLog, CancelApply
from planet.models.play import Play, PlayPay, MakeOver


class CMiniProgramPersonalCenter(BASEAPPROVAL):

    @phone_required
    def my_wallet(self):
        """我的钱包页（消费记录、提现记录）"""
        args = request.args.to_dict()
        date, option = args.get('date'), args.get('option')
        user = User.query.filter(User.isdelete == false(), User.USid == getattr(request, 'user').id).first_('请重新登录')
        if date and not re.match(r'^20\d{2}-\d{2}$', str(date)):
            raise ParamsError('date 格式错误')
        year, month = str(date).split('-') if date else (datetime.now().year, datetime.now().month)
        if option == 'expense':
            transactions, total = self._get_transactions(user, year, month, args)
        elif option == 'withdraw':
            transactions, total = self._get_withdraw(user, year, month)
        else:
            raise ParamsError('type 参数错误')
        user_wallet = UserWallet.query.filter(UserWallet.isdelete == false(), UserWallet.USid == user.USid).first()
        if user_wallet:
            uwcash = user_wallet.UWcash
        else:
            with db.auto_commit():
                user_wallet_instance = UserWallet.create({
                    'UWid': str(uuid.uuid1()),
                    'USid': user.USid,
                    'CommisionFor': ApplyFrom.user.value,
                    'UWbalance': Decimal('0.00'),
                    'UWtotal': Decimal('0.00'),
                    'UWcash': Decimal('0.00'),
                    'UWexpect': Decimal('0.00')
                })
                db.session.add(user_wallet_instance)
                uwcash = 0
        response = {'uwcash': uwcash,
                    'transactions': transactions,
                    'total': total
                    }
        return Success(data=response)

    def _get_transactions(self, user, year, month, args):
        pp_query = self._income_query_expression(
            (PlayPay.PPpayMount.label('amount'),
             PlayPay.createtime.label('time'),
             Play.PLtitle.label('title'),
             EnterLog.USid.label('usid')),
            (or_(Play.PLcreate == user.USid, EnterLog.USid == user.USid),
             EnterLog.ELstatus.in_((EnterLogStatus.success.value,
                                    EnterLogStatus.refund.value,
                                    EnterLogStatus.canceled.value)),
             PlayPay.PPpayType == PlayPayType.enterlog.value,
             extract('month', PlayPay.createtime) == month,
             extract('year', PlayPay.createtime) == year)
        ).all()
        transactions = [{'amount': i[0] if i[3] != user.USid else -i[0],
                         'time': i[1], 'title': '[报名] ' + i[2] if i[3] == user.USid else '[团员报名] ' + i[2]
                         } for i in pp_query if i[0] is not None]
        mo_query = db.session.query(PlayPay.PPpayMount.label('amount'),
                                    PlayPay.createtime.label('time'),
                                    Play.PLtitle.label('title'),
                                    MakeOver.MOsuccessor.label('usid')).join(
            MakeOver, MakeOver.MOid == PlayPay.PPcontent
        ).join(Play, Play.PLid == MakeOver.PLid
               ).filter(Play.isdelete == false(),
                        MakeOver.isdelete == false(),
                        PlayPay.isdelete == false(),
                        PlayPay.PPpayType == PlayPayType.undertake.value,
                        MakeOver.MOstatus == MakeOverStatus.success.value,
                        or_(MakeOver.MOassignor == user.USid, MakeOver.MOsuccessor == user.USid),
                        extract('month', PlayPay.createtime) == month,
                        extract('year', PlayPay.createtime) == year
                        ).all()
        [transactions.append({'amount': i[0] if i[3] == user.USid else -i[0],
                              'time': i[1],
                              'title': '[承接] ' + i[2] if i[3] == user.USid else '[转让] ' + i[2]}
                             ) for i in mo_query if i[0] is not None]
        ca_query = self._expenditure_query_expression(
            (CancelApply.CAPprice.label('amout'),
             CancelApply.createtime.label('time'),
             Play.PLtitle.label('title'),
             EnterLog.USid.label('usid')),
            (or_(Play.PLcreate == user.USid, EnterLog.USid == user.USid),
             EnterLog.ELstatus.in_((EnterLogStatus.success.value,
                                    EnterLogStatus.refund.value,
                                    EnterLogStatus.canceled.value)),
             extract('month', CancelApply.createtime) == month,
             extract('year', CancelApply.createtime) == year)
        ).all()
        [transactions.append({'amount': i[0] if i[3] == user.USid else -i[0],
                              'time': i[1],
                              'title': '[退团] ' + i[2] if i[3] == user.USid else '[团员退出] ' + i[2]}
                             ) for i in ca_query if i[0] is not None]
        transactions.sort(key=lambda x: x.get('time'), reverse=True)
        total = sum(i.get('amount', 0) for i in transactions)
        for item in transactions:
            item['amount'] = '+ ¥{}'.format(item['amount']) if item['amount'] > 0 else '- ¥{}'.format(
                -item['amount']) if item['amount'] != 0 else '  ¥{}'.format(-item['amount'])
        total = ' ¥{}'.format(total) if total >= 0 else ' - ¥{}'.format(-total)

        # 筛选后重新分页
        page_num = args.get('page_num', 1)
        page_size = args.get('page_size', 15)
        page_num = int(page_num) if re.match(r'^\d+$', str(page_num)) and int(page_num) > 0 else 1
        page_size = int(page_size) if re.match(r'^\d+$', str(page_size)) and int(page_size) > 0 else 15
        mount = len(transactions)
        page_all = math.ceil(float(mount) / int(page_size))
        start = (page_num - 1) * page_size
        end = page_num * page_size
        transactions = transactions[start: end]
        request.page_all = page_all
        request.mount = mount
        return transactions, total

    @staticmethod
    def _get_withdraw(user, year, month):
        res = db.session.query(CashNotes.CNstatus, CashNotes.createtime, CashNotes.CNcashNum
                               ).filter(CashNotes.isdelete == false(), CashNotes.USid == user.USid,
                                        extract('month', CashNotes.createtime) == month,
                                        extract('year', CashNotes.createtime) == year
                                        ).order_by(CashNotes.createtime.desc(), origin=True).all_with_page()
        withdraw = [{'title': ApprovalAction(i[0]).zh_value, 'time': i[1], 'amount': i[2]}
                    for i in res if i[0] is not None]
        total = sum(i.get('amount', 0) for i in withdraw)
        for item in withdraw:
            item['amount'] = '¥{}'.format(item['amount'])
        total = '¥{}'.format(total)
        return withdraw, total

    @phone_required
    def guide_certification(self):
        """导游申请认证"""
        from planet.control.CUser import CUser
        cuser = CUser()
        data = parameter_required()
        user = User.query.filter_by_(USid=getattr(request, 'user').id).first_('请重新登录')
        guide = Guide.query.filter_by_(USid=user.USid).first()
        if guide:
            raise ParamsError('已提交过认证')
        gurealname, gutelphone = data.get('gurealname'), data.get('gutelphone')
        guidentification = data.get('guidentification')
        if not re.match(r'^1\d{10}$', gutelphone):
            raise ParamsError('请填写正确的手机号码')
        checked_name = cuser._verify_chinese(gurealname)
        if not checked_name or len(checked_name[0]) < 2:
            raise ParamsError('请正确填写真实姓名')
        if len(guidentification) < 18:
            raise ParamsError('请正确填写身份证号码')
        oldname = user.USrealname
        oldidentitynumber = user.USidentification
        cuser.check_idcode({'usrealname': gurealname, 'usidentification': guidentification}, user)  # 调用实名认证
        with db.auto_commit():
            guide_instance = Guide.create({'GUid': str(uuid.uuid1()),
                                           'USid': user.USid,
                                           'GUrealname': gurealname,
                                           'GUtelphone': gutelphone,
                                           'GUidentification': guidentification,
                                           'GUimg': data.get('guimg'),
                                           'GUstatus': GuideApplyStatus.auditing.value
                                           })
            db.session.add(guide_instance)

            if oldname and oldname != gurealname:
                current_app.logger.info('old name: {} ; new name: {}'.format(oldname, gurealname))
                db.session.add(CoveredCertifiedNameLog.create({'CNLid': str(uuid.uuid1()),
                                                               'OldName': oldname,
                                                               'NewName': gurealname,
                                                               'OldIdentityNumber': oldidentitynumber,
                                                               'NewIdentityNumber': guidentification
                                                               }))
        avid = super(CMiniProgramPersonalCenter, self).create_approval('toguide', user.USid, guide_instance.GUid)
        auto_agree_task.apply_async(args=[avid], countdown=5, expires=1 * 60, )  # 提交5秒后自动通过
        return Success('提交成功', {'guid': guide_instance.GUid})

    @phone_required
    def guide(self):
        user = User.query.filter_by_(USid=getattr(request, 'user').id).first_('请重新登录')
        guide = Guide.query.filter_by_(USid=user.USid).first()
        if not guide:
            return Success(data={})
        guide.hide('GUid')
        guide.fill('gustatus_en', GuideApplyStatus(guide.GUstatus).name)
        guide.fill('gustatus_zh', GuideApplyStatus(guide.GUstatus).zh_value)
        return Success(data=guide)

    @phone_required
    def data_statistics(self):
        """数据统计"""
        args = parameter_required('option')
        option = args.get('option')
        usid = getattr(request, 'user').id
        year = validate_arg(r'^\d{4}$', args.get('year'), '年份格式错误') if args.get('year') else None
        if option == 'personnel':  # 人员数据
            total_num, date = self._total_num(year, usid)
            res = {'total_num': total_num,
                   'people_num': self._total_people_num(year, usid, date),
                   'repeat_num': self._repeat_num(year, usid, date),
                   'repeat_user': self._repeat_user(year, usid),
                   'date': date
                   }
            return Success(data=res)
        elif option == 'team':  # 团队数据
            return self._team_num(year, usid)
        elif option == 'finance':  # 收支统计(首页)
            return self._total_finance(usid)
        elif option == 'transaction':  # 收支统计(年月视图及详情)
            income, expenditure, date = self.income_and_expenditure_statistics(year, usid)
            details = self._transaction_details(year, args, usid)
            return Success(data={'income': income,
                                 'expenditure': expenditure,
                                 'date': date,
                                 'details': details
                                 })
        elif option == 'scenicspot':  # 景区数据
            raise ParamsError('功能暂未开放，敬请期待')
        elif option == 'repeat':  # 参团2次及以上用户
            return Success(data=self._repeat_user(year, usid, limit=False))
        else:
            raise ParamsError('option 参数错误')

    @staticmethod
    def _query_expression(filter_obj, filter_args):
        return db.session.query(*filter_obj).join(
            Play, Play.PLid == EnterLog.PLid
        ).filter(Play.isdelete == false(),
                 EnterLog.isdelete == false(),
                 EnterLog.ELstatus == EnterLogStatus.success.value,
                 *filter_args)

    def _total_num(self, year, usid):
        """参团总人数"""
        if year:
            date = [i for i in range(1, 13)]
            res = [self._query_expression((func.count(EnterLog.ELid),),
                                          (Play.PLcreate == usid,
                                           extract('year', Play.createtime) == year,
                                           extract('month', Play.createtime) == month)
                                          ).scalar() or 0 for month in date]
        else:
            num = self._query_expression((func.count(EnterLog.ELid), extract('year', Play.createtime)),
                                         (Play.PLcreate == usid,)
                                         ).group_by(extract('year', Play.createtime)).all()
            num.sort(key=lambda x: x[1])
            res, date = [], []
            for i in num:
                res.append(i[0])
                date.append(i[1])
        return res, date

    def _total_people_num(self, year, usid, date):
        """参团用户数"""
        return [self._query_expression((EnterLog.USid,),
                                       (Play.PLcreate == usid,
                                        extract('year', Play.createtime) == year,
                                        extract('month', Play.createtime) == month)
                                       ).group_by(EnterLog.USid).count() or 0 for month in range(1, 13)
                ] if year else [self._query_expression((EnterLog.USid,),
                                                       (Play.PLcreate == usid,
                                                        extract('year', Play.createtime) == year
                                                        )).group_by(EnterLog.USid).count() or 0 for year in date]

    def _repeat_num(self, year, usid, date):
        """参团2次及以上用户数"""
        res = []
        if year:
            for month in range(1, 13):
                num = self._query_expression((EnterLog.USid, func.count(EnterLog.USid)),
                                             (Play.PLcreate == usid,
                                              extract('year', Play.createtime) == year,
                                              extract('month', Play.createtime) == month)
                                             ).group_by(EnterLog.USid).all()
                repeat_usid = [i[0] for i in num if i[1] > 1]
                res.append(len(repeat_usid))
        else:
            for year in date:
                num = self._query_expression((EnterLog.USid, func.count(EnterLog.USid)),
                                             (Play.PLcreate == usid,
                                              extract('year', Play.createtime) == year)
                                             ).group_by(EnterLog.USid).all()
                repeat_usid = [i[0] for i in num if i[1] > 1]
                res.append(len(repeat_usid))
        return res

    def _repeat_user(self, year, usid, limit=5):
        """参团2次以上用户"""
        if not year:
            year = datetime.now().year
        repeat = self._query_expression((EnterLog.USid, func.count(EnterLog.USid)),
                                        (Play.PLcreate == usid,
                                         extract('year', Play.createtime) == year)
                                        ).group_by(EnterLog.USid)
        if limit:
            repeat = repeat.limit(limit)
        repeat = repeat.all()
        repeat.sort(key=lambda x: x[1], reverse=True)
        res = []
        for i in repeat:
            if i[1] > 1:
                user = User.query.filter(User.isdelete == false(), User.USid == i[0]).first()
                if not user:
                    continue
                res.append({'usheader': user.USheader,
                            'usname': user.USname,
                            'repeat': i[1]})
        return res

    @staticmethod
    def _team_num(year, usid):
        if year:
            date = [i for i in range(1, 13)]
            res = [db.session.query(func.count(Play.PLid)
                                    ).filter(Play.isdelete == false(),
                                             Play.PLcreate == usid,
                                             extract('year', Play.createtime) == year,
                                             extract('month', Play.createtime) == month).scalar() for month in date]
        else:
            num = db.session.query(extract('year', Play.createtime), func.count(Play.PLid)
                                   ).filter(Play.isdelete == false(),
                                            Play.PLcreate == usid).group_by(extract('year', Play.createtime)).all()
            num.sort(key=lambda x: x[0])
            res, date = [], []
            for i in num:
                res.append(i[1])
                date.append(i[0])
        return Success(data={'team_num': res,
                             'date': date})

    @staticmethod
    def _income_query_expression(filter_obj, filter_args):
        return db.session.query(*filter_obj).join(
            EnterLog, EnterLog.ELid == PlayPay.PPcontent
        ).join(Play, Play.PLid == EnterLog.PLid
               ).filter(Play.isdelete == false(),
                        EnterLog.isdelete == false(),
                        PlayPay.isdelete == false(),
                        *filter_args)

    @staticmethod
    def _expenditure_query_expression(filter_obj, filter_args):
        return db.session.query(*filter_obj).join(
            EnterLog, EnterLog.ELid == CancelApply.ELid
        ).join(Play, Play.PLid == EnterLog.PLid
               ).filter(Play.isdelete == false(),
                        EnterLog.isdelete == false(),
                        CancelApply.isdelete == false(),
                        *filter_args)

    def _total_finance(self, usid):
        now = datetime.now()
        total_income_query = self._income_query_expression(
            (func.sum(PlayPay.PPpayMount),),
            (Play.PLcreate == usid,
             EnterLog.ELstatus == EnterLogStatus.success.value))
        total_income = total_income_query.scalar() or 0  # 总收益

        refund_expenditure_query = self._expenditure_query_expression(
            (func.sum(CancelApply.CAPprice),),
            (Play.PLcreate == usid,
             EnterLog.ELstatus.in_((EnterLogStatus.cancel.value,
                                    EnterLogStatus.refund.value,
                                    EnterLogStatus.canceled.value))))
        refund_expenditure = refund_expenditure_query.scalar() or 0  # 退团支出

        sign_up_expenditure_query = self._income_query_expression(
            (func.sum(PlayPay.PPpayMount),),
            (EnterLog.USid == usid,
             EnterLog.ELstatus == EnterLogStatus.success.value))
        sign_up_expenditure = sign_up_expenditure_query.scalar() or 0  # 报名支出

        current_month_income = total_income_query.filter(extract('year', PlayPay.createtime) == now.year,
                                                         extract('month', PlayPay.createtime) == now.month
                                                         ).scalar() or 0
        current_month_expenditure = float(refund_expenditure_query.filter(
            extract('year', CancelApply.createtime) == now.year,
            extract('month', CancelApply.createtime) == now.month).scalar() or 0) + float(
            sign_up_expenditure_query.filter(
                extract('year', PlayPay.createtime) == now.year,
                extract('month', PlayPay.createtime) == now.month).scalar() or 0)

        return Success(data={'total': {'income': total_income,
                                       'expenditure': refund_expenditure + sign_up_expenditure},
                             'current': {'income': current_month_income,
                                         'expenditure': current_month_expenditure,
                                         'month': '{}月账单'.format(now.month)}
                             })

    def income_and_expenditure_statistics(self, year, usid):
        if year:
            date = [i for i in range(1, 13)]
            income = [self._income_query_expression(
                (func.sum(PlayPay.PPpayMount),),
                (Play.PLcreate == usid,
                 extract('year', PlayPay.createtime) == year,
                 extract('month', PlayPay.createtime) == month,
                 EnterLog.ELstatus == EnterLogStatus.success.value)).scalar() or 0 for month in date]

            refund_expenditure = [self._expenditure_query_expression(
                (func.sum(CancelApply.CAPprice),),
                (Play.PLcreate == usid,
                 extract('year', CancelApply.createtime) == year,
                 extract('month', CancelApply.createtime) == month,
                 EnterLog.ELstatus.in_((EnterLogStatus.cancel.value,
                                        EnterLogStatus.refund.value,
                                        EnterLogStatus.canceled.value)))).scalar() or 0 for month in date]

            sign_up_expenditure = [self._income_query_expression(
                (func.sum(PlayPay.PPpayMount),),
                (EnterLog.USid == usid,
                 extract('year', PlayPay.createtime) == year,
                 extract('month', PlayPay.createtime) == month,
                 EnterLog.ELstatus == EnterLogStatus.success.value)).scalar() or 0 for month in date]

            expenditure = list(map(lambda x: x[0] + x[1], zip(refund_expenditure, sign_up_expenditure)))

        else:
            temp = 2019
            date = []
            while temp <= datetime.now().year:
                date.append(temp)
                temp += 1
            if len(date) > 5:
                date = date[-5:]
            income = [self._income_query_expression(
                (func.sum(PlayPay.PPpayMount),),
                (Play.PLcreate == usid,
                 extract('year', PlayPay.createtime) == year,
                 EnterLog.ELstatus == EnterLogStatus.success.value)).scalar() or 0 for year in date]

            sign_up_expenditure = [self._income_query_expression(
                (func.sum(PlayPay.PPpayMount),),
                (EnterLog.USid == usid,
                 extract('year', PlayPay.createtime) == year,
                 EnterLog.ELstatus == EnterLogStatus.success.value)).scalar() or 0 for year in date]

            refund_expenditure = [self._expenditure_query_expression(
                (func.sum(CancelApply.CAPprice),),
                (Play.PLcreate == usid,
                 extract('year', CancelApply.createtime) == year,
                 EnterLog.ELstatus.in_((EnterLogStatus.cancel.value,
                                        EnterLogStatus.refund.value,
                                        EnterLogStatus.canceled.value)))).scalar() or 0 for year in date]

            expenditure = list(map(lambda x: x[0] + x[1], zip(refund_expenditure, sign_up_expenditure)))
        return income, expenditure, date

    def _transaction_details(self, year, args, usid):
        if not year:
            return
        month = args.get('month') if args.get('month') else datetime.now().month
        filter_arg = args.get('filter')
        pp_detail = self._income_query_expression(
            (PlayPay.PPpayMount.label('amount'),
             PlayPay.createtime.label('time'),
             Play.PLtitle.label('title'),
             EnterLog.USid.label('usid'),
             User.USname.label('usname')),
            (or_(Play.PLcreate == usid, EnterLog.USid == usid),
             EnterLog.ELstatus.in_((EnterLogStatus.success.value,
                                    EnterLogStatus.refund.value,
                                    EnterLogStatus.canceled.value)),
             extract('month', PlayPay.createtime) == month,
             extract('year', PlayPay.createtime) == year)
        ).join(User, User.USid == EnterLog.USid).all()
        transactions = [{'amount': i[0] if i[3] != usid else -i[0],
                         'time': i[1], 'title': '[报名] ' + i[2] if i[3] == usid else '[团员报名] ' + i[2],
                         'usname': i[4]
                         } for i in pp_detail if i[0] is not None]
        ca_detail = self._expenditure_query_expression(
            (CancelApply.CAPprice.label('amout'),
             CancelApply.createtime.label('time'),
             Play.PLtitle.label('title'),
             EnterLog.USid.label('usid'),
             User.USname.label('usname')),
            (or_(Play.PLcreate == usid, EnterLog.USid == usid),
             EnterLog.ELstatus.in_((EnterLogStatus.success.value,
                                    EnterLogStatus.refund.value,
                                    EnterLogStatus.canceled.value)),
             extract('month', CancelApply.createtime) == month,
             extract('year', CancelApply.createtime) == year)
        ).join(User, User.USid == EnterLog.USid).all()
        [transactions.append({'amount': i[0] if i[3] == usid else -i[0],
                              'time': i[1],
                              'title': '[退团] ' + i[2] if i[3] == usid else '[团员退出] ' + i[2],
                              'usname': i[4]}
                             ) for i in ca_detail if i[0] is not None]
        if filter_arg == 'income':
            transactions = list(filter(lambda x: x.get('amount') > 0, transactions))
        elif filter_arg == 'expenditure':
            transactions = list(filter(lambda x: x.get('amount') < 0, transactions))
        transactions.sort(key=lambda x: x.get('time'), reverse=True)
        for item in transactions:
            item['income'] = True if item['amount'] >= 0 else False
            item['amount'] = '+ ¥{}'.format(item['amount']) if item['amount'] >= 0 else '- ¥{}'.format(-item['amount'])
        # 筛选后重新分页
        page_num = args.get('page_num', 1)
        page_size = args.get('page_size', 15)
        page_num = int(page_num) if re.match(r'^\d+$', str(page_num)) and int(page_num) > 0 else 1
        page_size = int(page_size) if re.match(r'^\d+$', str(page_size)) and int(page_size) > 0 else 15
        mount = len(transactions)
        page_all = math.ceil(float(mount) / int(page_size))
        start = (page_num - 1) * page_size
        end = page_num * page_size
        transactions = transactions[start: end]
        request.page_all = page_all
        request.mount = mount
        return transactions
