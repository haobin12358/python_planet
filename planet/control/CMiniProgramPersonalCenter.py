import re
import uuid
import math
from datetime import datetime
from decimal import Decimal
from flask import current_app, request
from sqlalchemy import false, extract, or_
from planet.common.params_validates import parameter_required
from planet.common.success_response import Success
from planet.common.token_handler import phone_required
from planet.common.error_response import ParamsError
from planet.config.enums import EnterLogStatus, ApplyFrom, ApprovalAction, GuideApplyStatus
from planet.control.BaseControl import BASEAPPROVAL
from planet.extensions.register_ext import db
from planet.extensions.tasks import auto_agree_task
from planet.models.scenicspot import Guide
from planet.models.user import User, UserWallet, CashNotes, CoveredCertifiedNameLog
from planet.models.join import EnterLog, CancelApply
from planet.models.play import Play, PlayPay


class CMiniProgramPersonalCenter(BASEAPPROVAL):

    @phone_required
    def my_wallet(self):
        """我的钱包页（消费记录、提现记录）"""
        args = request.args.to_dict()
        date, option = args.get('date'), args.get('option')
        transactions, withdraw = None, None
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

    @staticmethod
    def _get_transactions(user, year, month, args):
        pp_query = db.session.query(PlayPay.PPpayMount.label('amount'),
                                    PlayPay.createtime.label('time'),
                                    Play.PLtitle.label('title'),
                                    EnterLog.USid.label('usid')
                                    ).join(EnterLog,
                                           EnterLog.ELid == PlayPay.PPcontent
                                           ).join(Play, Play.PLid == EnterLog.PLid
                                                  ).filter(PlayPay.isdelete == false(),
                                                           EnterLog.isdelete == false(),
                                                           Play.isdelete == false(),
                                                           or_(Play.PLcreate == user.USid, EnterLog.USid == user.USid),
                                                           EnterLog.ELstatus.in_((EnterLogStatus.success.value,
                                                                                  EnterLogStatus.refund.value,
                                                                                  EnterLogStatus.canceled.value)),
                                                           extract('month', PlayPay.createtime) == month,
                                                           extract('year', PlayPay.createtime) == year
                                                           ).all()
        transactions = [{'amount': i[0] if i[3] != user.USid else -i[0],
                         'time': i[1], 'title': '[报名] ' + i[2] if i[3] == user.USid else '[团员报名] ' + i[2]
                         } for i in pp_query if i[0] is not None]
        ca_query = db.session.query(CancelApply.CAPprice.label('amout'),
                                    CancelApply.createtime.label('time'),
                                    Play.PLtitle.label('title'),
                                    EnterLog.USid.label('usid')
                                    ).join(EnterLog,
                                           EnterLog.ELid == CancelApply.ELid
                                           ).join(Play, Play.PLid == EnterLog.PLid
                                                  ).filter(EnterLog.isdelete == false(),
                                                           CancelApply.isdelete == false(),
                                                           Play.isdelete == false(),
                                                           or_(Play.PLcreate == user.USid, EnterLog.USid == user.USid),
                                                           EnterLog.ELstatus.in_((EnterLogStatus.success.value,
                                                                                  EnterLogStatus.refund.value,
                                                                                  EnterLogStatus.canceled.value)),
                                                           extract('month', CancelApply.createtime) == month,
                                                           extract('year', CancelApply.createtime) == year
                                                           ).all()
        [transactions.append({'amount': i[0] if i[3] == user.USid else -i[0],
                              'time': i[1],
                              'title': '[退团] ' + i[2] if i[3] == user.USid else '[团员退出] ' + i[2]}
                             ) for i in ca_query if i[0] is not None]
        transactions.sort(key=lambda x: x.get('time'), reverse=True)
        total = sum(i.get('amount', 0) for i in transactions)
        for item in transactions:
            item['amount'] = '+ ¥{}'.format(item['amount']) if item['amount'] >= 0 else '- ¥{}'.format(-item['amount'])
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



