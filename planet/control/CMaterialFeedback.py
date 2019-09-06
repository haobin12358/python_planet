import json
import uuid
from decimal import Decimal

from flask import request, current_app
from sqlalchemy import false

from planet.common.error_response import ParamsError
from planet.common.params_validates import parameter_required
from planet.common.success_response import Success
from planet.common.token_handler import phone_required, get_current_user, token_required, is_admin, admin_required
from planet.config.enums import LinkageShareType, UserMaterialFeedbackStatus, ApplyFrom, TicketsOrderStatus
from planet.extensions.register_ext import db
from planet.models import UserMaterialFeedback, MaterialFeedbackLinkage, Linkage, Ticket, TicketLinkage, UserWallet, \
    User, TicketsOrder


class CMaterialFeedback():
    def __init__(self):
        pass

    @phone_required
    def create(self):
        data = parameter_required('tsoid')
        tsoid = data.get('tsoid')
        # tiid 合法性校验
        # ticket = Ticket.query.filter_by(TIid=tiid, isdelete=false).first_('ttid 失效')
        tso = TicketsOrder.query.filter_by(
            TSOid=tsoid, isdelete=False, TSOstatus=TicketsOrderStatus.completed.value).first_('尚未发票')
        ticket = Ticket.query.filter(Ticket.TIid == tso.TIid, Ticket.isdelete == false()).first_('ttid 失效')
        # umf = UserMaterialFeedback.query.filter_by()
        user = get_current_user()
        mfls = data.get('mfls', [])
        umf_dict = self._create_umdetails(data)
        # todo 同步随笔
        with db.auto_commit():
            umf_dict.update({
                'UMFid': str(uuid.uuid1()),
                'TIid': tso.TIid,
                'TSOid': tso.TSOid,
                'USid': user.USid
            })
            umf = UserMaterialFeedback.create(umf_dict)
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

    @admin_required
    def refund(self):
        data = parameter_required('umfid')
        umfid = data.get('umfid')

        with db.auto_commit():
            umf = UserMaterialFeedback.query.filter_by(
                UMFid=umfid, UMFstatus=UserMaterialFeedbackStatus.wait.value, isdelete=False).first_('素材反馈已处理')
            ticket = Ticket.query.filter_by(TIid=umf.TIid, isdelete=False).first_('票务已删除')
            # 修改状态
            umf.UMFstatus = UserMaterialFeedbackStatus.refund.value

            price = Decimal(str(ticket.TIprice)).quantize(Decimal('0.00'))
            # 退钱
            user_wallet = UserWallet.query.filter_by(USid=umf.USid).first()
            if user_wallet:
                current_app.logger.info(
                    'get uw before change UWbalance = {}, UWtotal= {} UWcash = {}'.format(
                        user_wallet.UWbalance, user_wallet.UWtotal, user_wallet.UWcash))

                user_wallet.UWbalance = Decimal(str(user_wallet.UWbalance or 0)) + price
                user_wallet.UWtotal = Decimal(str(user_wallet.UWtotal or 0)) + price
                user_wallet.UWcash = Decimal(str(user_wallet.UWcash or 0)) + price
                current_app.logger.info(
                    'get uw after change UWbalance = {}, UWtotal= {} UWcash = {}'.format(
                        user_wallet.UWbalance, user_wallet.UWtotal, user_wallet.UWcash))

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
            # 同一购票记录的其他凭证修改状态为已处理
            UserMaterialFeedback.query.filter(
                UserMaterialFeedback.UMFid != umfid,
                                              UserMaterialFeedback.isdelete == false(),
                                              UserMaterialFeedback.UMFstatus != UserMaterialFeedbackStatus.reject.value,
                                              UserMaterialFeedback.TSOid == umf.TSOid).update(
                {'UMFstatus': UserMaterialFeedbackStatus.refund.value})

        return Success

    @admin_required
    def refuse(self):
        data = parameter_required('umfid')
        umfid = data.get('umfid')
        with db.auto_commit():
            umf = UserMaterialFeedback.query.filter_by(
                UMFid=umfid, UMFstatus=UserMaterialFeedbackStatus.wait.value, isdelete=False).first_('素材反馈已处理')
            # ticket = Ticket.query.filter_by(TIid=umf.TIid, isdelete=False).first_('票务已删除')
            umf.UMFstatus = UserMaterialFeedbackStatus.reject.value
        return Success('已拒绝')

    @token_required
    def get(self):
        data = parameter_required('tsoid')
        tsoid = data.get('tsoid')
        # tiid 合法性校验
        tso = TicketsOrder.query.filter_by(
            TSOid=tsoid, isdelete=False, TSOstatus=TicketsOrderStatus.completed.value).first_('尚未出票，请稍后')

        # Ticket.query.filter_by(TIid=tiid, isdelete=False).first_('ttid 失效')
        filter_args = {
            UserMaterialFeedback.TIid == tso.TIid,
            UserMaterialFeedback.TSOid == tsoid,
            UserMaterialFeedback.USid == getattr(request, 'user').id,
            UserMaterialFeedback.isdelete == false()
        }
        umf = UserMaterialFeedback.query.filter(*filter_args).order_by(UserMaterialFeedback.createtime.desc()).first()
        if not umf:
            return Success()
        self._fill_umf(umf)
        return Success(data=umf)

    @admin_required
    def list(self):
        data = parameter_required('tiid')
        tiid = data.get('tiid')
        # tiid 合法性校验
        Ticket.query.filter_by(TIid=tiid, isdelete=False).first_('ttid 失效')
        umfs = UserMaterialFeedback.query.filter_by(TIid=tiid, isdelete=False).all_with_page()
        for umf in umfs:
            self._fill_umf(umf)
            self._fill_user(umf)
        return Success(data=umfs)

    def get_ticket_linkage(self):
        data = parameter_required('tiid')
        tiid = data.get('tiid')
        Ticket.query.filter_by(TIid=tiid, isdelete=False).first_('票已删')
        tl_list = TicketLinkage.query.filter(
            TicketLinkage.isdelete == false(),
            TicketLinkage.TIid == tiid,
        ).all()
        for tl in tl_list:
            self._fill_mfl(tl)
        return Success(data=tl_list)

    @admin_required
    def get_details(self):
        data = parameter_required('umfid')
        umfid = data.get('umfid')
        umf = UserMaterialFeedback.query.filter_by(UMFid=umfid, isdelete=False).first_('素材反馈已删除')

        self._fill_umf(umf)
        self._fill_user(umf)
        return Success(data=umf)

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

    def _create_umdetails(self, data):
        """内容"""
        text, image, video = data.get('text'), data.get('image'), data.get('video')
        # if image:
        #     current_app.logger.error("图片校验测试")
        #     current_app.logger.error(mp_miniprogram.img_sec_check(image))
        if image and not isinstance(image, list):
            raise ParamsError('image 格式错误')
        if image and video:
            raise ParamsError('不能同时选择图片和视频')
        if image and len(image) > 9:
            raise ParamsError('最多可上传9张图片')
        video = {'url': self._check_upload_url(video.get('url')),
                 'thumbnail': video.get('thumbnail'),
                 'duration': video.get('duration')
                 } if video else None
        content = {'text': text,
                   'image': [self._check_upload_url(i, msg='图片格式错误, 请检查后重新上传') for i in image] if image else None,
                   'video': video
                   }
        content = json.dumps(content)
        return {'UMFdetails': content,
                'UMFlocation': data.get('umlocation')
                }

    @staticmethod
    def _check_upload_url(url, msg='视频上传出错，请重新上传(视频时长需大于3秒，小于60秒)'):
        if not url or str(url).endswith('undefined'):
            raise ParamsError(msg)
        return url

    def _fill_umf(self, umf):
        umf.fields = ['UMFid', 'UMFlocation', 'UMFstatus', 'TIid', 'TSOid']
        content = json.loads(umf.UMFdetails)
        umf.fill('text', content.get('text', '...'))
        umf.fill('image', content.get('image'))
        umf.fill('video', content.get('video'))
        if content.get('image'):
            showtype = 'image'
        elif content.get('video'):
            showtype = 'video'
        else:
            showtype = 'text'
        umf.fill('showtype', showtype)

        umf.add('createtime')
        mfl_list = MaterialFeedbackLinkage.query.filter_by(UMFid=umf.UMFid, isdelete=False).all()
        for mfl in mfl_list:
            self._fill_mfl(mfl)
        umf.fill('mfls', mfl_list)
