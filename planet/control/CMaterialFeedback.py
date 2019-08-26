import uuid
from decimal import Decimal

from flask import request
from sqlalchemy import false

from planet.common.error_response import ParamsError
from planet.common.params_validates import parameter_required
from planet.common.success_response import Success
from planet.common.token_handler import phone_required, get_current_user, token_required, is_admin, admin_required
from planet.config.enums import LinkageShareType, UserMaterialFeedbackStatus, ApplyFrom
from planet.extensions.register_ext import db
from planet.models import UserMaterialFeedback, MaterialFeedbackLinkage, Linkage, Ticket, TicketLinkage, UserWallet, \
    User


class CMaterialFeedback():
    def __init__(self):
        pass

    @phone_required
    def create(self):
        data = parameter_required('tiid')
        tiid = data.get('tiid')
        # tiid 合法性校验
        ticket = Ticket.query.filter_by(TIid=tiid, isdelete=false).first_('ttid 失效')
        # umf = UserMaterialFeedback.query.filter_by()
        user = get_current_user()
        umfdetails, umlocation, mfls = data.get('umfdetails'), data.get('umlocation'), data.get('mfls')
        with db.auto_commit():
            umf = UserMaterialFeedback.create({
                'UMFid': str(uuid.uuid1()),
                'UMFdetails': umfdetails,
                'UMFlocation': umlocation,
                'TIid': tiid,
                'USid': user.USid
            })
            db.session.add(umf)
            instance_list = []
            for mfl in mfls:
                self._check_mfl(mfl, ticket)
                mfl_instance = MaterialFeedbackLinkage.create({
                    'MFLid': str(uuid.uuid1()),
                    'UMFid': umf.UMFid,
                    'LIid': mfl.get('liid'),
                    'MFLimg': mfl.get('mflimg'),
                    'MFLlink': mfl.get('mfllink'),

                })
                instance_list.append(mfl_instance)
            db.session.add_all(instance_list)
        return Success('已经提交，请等待审核')

    @token_required
    def get(self):
        data = parameter_required('tiid')
        tiid = data.get('tiid')
        # tiid 合法性校验
        Ticket.query.filter_by(TIid=tiid, isdelete=false).first_('ttid 失效')
        filter_args = {
            UserMaterialFeedback.TIid == tiid,
            UserMaterialFeedback.isdelete == false()
        }
        # if not is_admin():
        filter_args.add(UserMaterialFeedback.USid == request.user.id)
        umf = UserMaterialFeedback.query.filter(*filter_args).first()
        if not umf:
            return Success()
        self._fill_umf(umf)
        return Success(data=umf)

    @admin_required
    def list(self):
        data = parameter_required('tiid')
        tiid = data.get('tiid')
        # tiid 合法性校验
        Ticket.query.filter_by(TIid=tiid, isdelete=false).first_('ttid 失效')
        umfs = UserMaterialFeedback.query.filter_by(TIid=tiid, isdelete=False).all_with_page()
        for umf in umfs:
            self._fill_umf(umf)
            self._fill_user(umf)
        return Success(data=umfs)

    def refund(self):
        data = parameter_required('umfid')
        umfid = data.get('umfid')

        with db.auto_commit():
            umf = UserMaterialFeedback.query.filter_by(
                UMFid=umfid, UMFstatus=UserMaterialFeedbackStatus.wait.value, isdelete=False).first_('素材反馈已处理')
            ticket = Ticket.query.filter_by(TIid=umf.TIid, isdelete=False).first_('票务已删除')
            price = Decimal(str(ticket.TIdeposit)).quantize(Decimal('0.00'))
            # 退钱
            user_wallet = UserWallet.query.filter_by(USid=umf.USid).first()
            if user_wallet:

                user_wallet.UWbalance = Decimal(str(user_wallet.UWbalance or 0)) + price
                user_wallet.UWtotal = Decimal(str(user_wallet.UWtotal or 0)) + price
                user_wallet.UWcash = Decimal(str(user_wallet.UWcash or 0)) + price
            else:
                user_wallet_instance = UserWallet.create({
                    'UWid': str(uuid.uuid1()),
                    'USid': umf.USid,
                    'UWbalance': price,
                    'UWtotal': price,
                    'UWcash': price,
                    # 'UWexpect': user_commision.UCcommission,
                    'CommisionFor': ApplyFrom.user.value
                })
                db.session.add(user_wallet_instance)
            # 同一票务的其他凭证修改状态为已处理
            UserMaterialFeedback.query.filter_by(UMFid=umfid, isdelete=False).update(
                {'UMFstatus': UserMaterialFeedbackStatus.refund.value})

        return Success

    def get_details(self):
        data = parameter_required('umfid')
        umfid = data.get('umfid')


    def _fill_umf(self, umf):
        umf.add('createtime')
        mfl_list = MaterialFeedbackLinkage.query.filter_by(UMFid=umf.UMFid, isdelete=False).all()
        for mfl in mfl_list:
            self._fill_mfl(mfl)
        umf.fill('mfls', mfl_list)

    def _fill_mfl(self, mfl):
        la = Linkage.query.filter(Linkage.LIid == mfl.LIid, Linkage.isdelete == false()).first()
        mfl.fill('linkage', la)

    def _check_mfl(self, mfl, ticket):
        tl = TicketLinkage.query.filter_by(
            LIid=mfl.get('liid'), TIid=ticket.TIid, isdelete=False).first_('联动平台不支持')

        la = Linkage.query.filter_by(LIid=tl.LIid, isdelete=False).first_('联动平台不支持')

        if la.LIshareType > LinkageShareType.screenshot.value and not mfl.get('mfllink'):
            raise ParamsError('该联动平台还需要链接')

    def _fill_user(self, umf):
        user = User.query.filter_by(USid=umf.USid, isdelete=False).first()
        if not user:
            umf.fill('USname', '旗行用户')
            umf.fill('UStelphone', '19817444373')
        else:
            umf.fill('USname', user.USname)
            umf.fill('UStelphone', user.UStelphone)
            umf.fill('USheader', user['USheader'])
