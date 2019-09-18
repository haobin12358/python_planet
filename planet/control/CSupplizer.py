import random
import re
import uuid
from decimal import Decimal
from threading import Thread
from flask import current_app
from sqlalchemy import or_, and_, false
from sqlalchemy.exc import IntegrityError
from werkzeug.security import generate_password_hash, check_password_hash

from planet.common.Inforsend import SendSMS
from planet.common.base_service import get_session
from planet.common.error_response import AuthorityError, ParamsError, DumpliError, NotFound, StatusError
from planet.common.params_validates import parameter_required
from planet.common.success_response import Success
from planet.common.token_handler import admin_required, is_admin, is_supplizer, token_required, is_tourist
from planet.config.enums import ProductBrandStatus, UserStatus, ProductStatus, ApplyFrom, NotesStatus, OrderMainStatus, \
    ApplyStatus, OrderRefundORAstate, OrderRefundOrstatus, WexinBankCode, AdminActionS, SupplizerGrade
from planet.control.BaseControl import BASEADMIN
from planet.extensions.register_ext import db, conn
from planet.extensions.validates.user import SupplizerListForm, SupplizerCreateForm, SupplizerGetForm, \
    SupplizerUpdateForm, SupplizerSendCodeForm, SupplizerResetPasswordForm, SupplizerChangePasswordForm, request, \
    GetVerifier, SetVerifier
from planet.models import Supplizer, ProductBrand, Products, UserWallet, SupplizerAccount, ManagerSystemNotes, \
    OrderMain, OrderRefundApply, OrderRefund, OrderPart, SupplizerDepositLog, Admin, TicketVerifier


class CSupplizer:
    def __init__(self):
        pass

    @admin_required
    def list(self):
        """供应商列表"""
        form = SupplizerListForm().valid_data()
        kw = form.kw.data
        mobile = form.mobile.data
        sustatus = form.sustatus.data
        option = form.option.data
        sugrade = form.sugrade.data
        # if sugrade is not None or sugrade:
        #     sugrade = int(sugrade)
        if str(sugrade).isdigit():
            sugrade = int(sugrade)
        else:
            sugrade = None

        if option == 'ticket':
            return self._list_ticket_sup()

        supplizers = Supplizer.query.filter_(
            Supplizer.isdelete == false(),
            Supplizer.SUgrade == sugrade,
            Supplizer.SUname.contains(kw),
            Supplizer.SUlinkPhone.contains(mobile),
            Supplizer.SUstatus == sustatus
        ).order_by(Supplizer.createtime.desc()).all_with_page()

        for supplizer in supplizers:
            supplizer.hide('SUpassword')
            if is_admin():
                pbs = ProductBrand.query.filter(
                    ProductBrand.isdelete == False,
                    ProductBrand.SUid == supplizer.SUid
                ).all()
                for pb in pbs:
                    if pb:
                        pb.pbstatus_zh = ProductBrandStatus(pb.PBstatus).zh_value
                        pb.add('pbstatus_zh')
                supplizer.fill('pbs', pbs)
            # 收益
            favor = UserWallet.query.filter(
                UserWallet.isdelete == False,
                UserWallet.USid == supplizer.SUid,
                UserWallet.CommisionFor == ApplyFrom.supplizer.value
            ).first()
            supplizer.fill('uwbalance', getattr(favor, 'UWbalance', 0))
            supplizer.fill('uwtotal', getattr(favor, 'UWtotal', 0))
            supplizer.fill('uwcash', getattr(favor, 'UWcash', 0))
            supplizer.fill('uwexpect', getattr(favor, 'UWexpect', 0))
            supplizer.fill('subaserate', supplizer.SUbaseRate or 0)
            supplizer.fill('sustatus_zh', UserStatus(supplizer.SUstatus).zh_value)
            supplizer.fill('sustatus_en', UserStatus(supplizer.SUstatus).name)
        return Success(data=supplizers)

    @staticmethod
    def _list_ticket_sup():
        sups = Supplizer.query.filter(Supplizer.isdelete == false(), Supplizer.SUstatus == UserStatus.usual.value,
                                      Supplizer.SUgrade == SupplizerGrade.ticket.value).all_with_page()
        for sup in sups:
            sup.fields = ['SUid', 'SUname', 'SUgrade', 'SUstatus']
            sup.fill('sustatus_zh', UserStatus(sup.SUstatus).zh_value)
            sup.fill('sugrade_zh', SupplizerGrade(sup.SUgrade).zh_value)
        return Success(data=sups)

    def create(self):
        """添加"""
        if is_admin():
            Admin.query.filter_by_(ADid=request.user.id).first_('账号状态异常')
            current_app.logger.info(">>>  Admin Create a Supplizer  <<<")
        elif is_tourist():
            current_app.logger.info(">>>  Tourist Uploading Supplizer Files  <<<")
        else:
            raise AuthorityError('无权限')
        form = SupplizerCreateForm().valid_data()
        pbids = form.pbids.data
        suid = str(uuid.uuid1())
        if is_admin():
            sustatus = UserStatus.usual.value
            sudeposit = form.sudeposit.data
        else:
            sustatus = UserStatus.auditing.value
            sudeposit = 0
        supassword = generate_password_hash(form.supassword.data) if form.supassword.data else None
        try:
            with db.auto_commit():
                supperlizer = Supplizer.create({
                    'SUid': suid,
                    'SUlinkPhone': form.sulinkphone.data,
                    'SUloginPhone': form.suloginphone.data,
                    'SUname': form.suname.data,
                    'SUlinkman': form.sulinkman.data,
                    'SUbaseRate': form.subaserate.data,
                    'SUaddress': form.suaddress.data,
                    'SUdeposit': sudeposit,
                    'SUstatus': sustatus,  # 管理员添加的可直接上线
                    'SUbanksn': form.subanksn.data,
                    'SUbankname': form.subankname.data,
                    'SUpassword': supassword,
                    'SUheader': form.suheader.data,
                    'SUcontract': form.sucontract.data,
                    'SUbusinessLicense': form.subusinesslicense.data,
                    'SUregisteredFund': form.suregisteredfund.data,
                    'SUmainCategory': form.sumaincategory.data,
                    'SUregisteredTime': form.suregisteredtime.data,
                    'SUlegalPerson': form.sulegalperson.data,
                    'SUemail': form.suemail.data,
                    'SUlegalPersonIDcardFront': form.sulegalpersonidcardfront.data,
                    'SUlegalPersonIDcardBack': form.sulegalpersonidcardback.data,
                    'SUgrade': form.sugrade.data or 0,
                })
                db.session.add(supperlizer)
                if is_admin():
                    BASEADMIN().create_action(AdminActionS.insert.value, 'Supplizer', suid)
                if pbids:
                    for pbid in pbids:
                        product_brand = ProductBrand.query.filter(
                            ProductBrand.isdelete == False,
                            ProductBrand.PBid == pbid
                        ).first()
                        if not product_brand:
                            raise NotFound('品牌不存在')
                        if product_brand.SUid:
                            raise DumpliError('品牌已有供应商')
                        product_brand.SUid = supperlizer.SUid
                        db.session.add(product_brand)
                if sudeposit and is_admin():
                    SupplizerDepositLog.create({
                        'SDLid': str(uuid.uuid1()),
                        'SUid': suid,
                        'SDLnum': Decimal(sudeposit),
                        'SDafter': Decimal(sudeposit),
                        'SDbefore': 0,
                        'SDLacid': request.user.id,
                    })
                    BASEADMIN().create_action(AdminActionS.insert.value, 'SupplizerDepositLog', str(uuid.uuid1()))
        except IntegrityError:
            raise ParamsError('手机号重复')
        return Success('创建成功', data={'suid': supperlizer.SUid})

    def update(self):
        """更新供应商信息"""
        if not is_admin() and not is_supplizer():
            raise AuthorityError()
        form = SupplizerUpdateForm().valid_data()
        pbids = form.pbids.data
        with db.auto_commit():
            supplizer = Supplizer.query.filter(Supplizer.isdelete == False, Supplizer.SUid == form.suid.data
                                               ).first_('供应商不存在')
            supplizer_dict = {
                'SUlinkPhone': form.sulinkphone.data,
                'SUname': form.suname.data,
                'SUlinkman': form.sulinkman.data,
                'SUaddress': form.suaddress.data,
                'SUbanksn': form.subanksn.data,
                'SUbankname': form.subankname.data,
                # 'SUpassword': generate_password_hash(form.supassword.data),  # todo 是不是要加上
                'SUheader': form.suheader.data,
                'SUcontract': form.sucontract.data,
                'SUbusinessLicense': form.subusinesslicense.data,
                'SUregisteredFund': form.suregisteredfund.data,
                'SUmainCategory': form.sumaincategory.data,
                'SUregisteredTime': form.suregisteredtime.data,
                'SUlegalPerson': form.sulegalperson.data,
                'SUemail': form.suemail.data,
                'SUlegalPersonIDcardFront': form.sulegalpersonidcardfront.data,
                'SUlegalPersonIDcardBack': form.sulegalpersonidcardback.data,
            }
            if is_admin():
                if form.subaserate.data:
                    supplizer_dict['SUbaseRate'] = form.subaserate.data,
                if isinstance(form.sustatus.data, int):
                    supplizer_dict['SUstatus'] = form.sustatus.data
                    if form.sustatus.data == UserStatus.usual.value and not supplizer.SUpassword:
                        supplizer_dict['SUpassword'] = generate_password_hash(supplizer.SUloginPhone)
                if form.sudeposit.data:
                    sudeposit = form.sudeposit.data
                    supplizer_dict['SUdeposit'] = Decimal(sudeposit)
                    if Decimal(sudeposit) != Decimal(getattr(supplizer, 'SUdeposit', 0)):  # 押金有变化时进行记录
                        depositlog = SupplizerDepositLog.create({
                            'SDLid': str(uuid.uuid1()),
                            'SUid': form.suid.data,
                            'SDLnum': Decimal(sudeposit) - Decimal(getattr(supplizer, 'SUdeposit', 0)),
                            'SDafter': Decimal(sudeposit),
                            'SDbefore': Decimal(getattr(supplizer, 'SUdeposit', 0)),
                            'SDLacid': request.user.id,
                        })
                        db.session.add(depositlog)
                        BASEADMIN().create_action(AdminActionS.insert.value, 'SupplizerDepositLog',str(uuid.uuid1()))

            supplizer.update(supplizer_dict, null='dont ignore')
            db.session.add(supplizer)
            if is_admin():
                BASEADMIN().create_action(AdminActionS.update.value, 'Supplizer', form.suid.data)
            if pbids and is_admin():
                for pbid in pbids:
                    product_brand = ProductBrand.query.filter(
                        ProductBrand.isdelete == False,
                        ProductBrand.PBid == pbid
                    ).first()
                    if not product_brand:
                        raise NotFound('品牌不存在')
                    if product_brand.SUid and product_brand.SUid != supplizer.SUid:
                        raise DumpliError('品牌已有供应商')
                    # if product_brand.PBstatus ==
                    # todo 品牌已下架
                    product_brand.SUid = form.suid.data
                    db.session.add(product_brand)
                # 删除其他的关联
                ProductBrand.query.filter(
                    ProductBrand.isdelete == False,
                    ProductBrand.SUid == form.suid.data,
                    ProductBrand.PBid.notin_(pbids)
                ).update({
                    'SUid': None
                }, synchronize_session=False)
        return Success('更新成功')

    @token_required
    def get(self):
        if not is_admin() and not is_supplizer():
            raise AuthorityError()
        form = SupplizerGetForm().valid_data()
        supplizer = form.supplizer
        self._fill_supplizer(supplizer)
        pbs = ProductBrand.query.filter(
            ProductBrand.isdelete == False,
            ProductBrand.SUid == supplizer.SUid
        ).all()
        for pb in pbs:
            if pb:
                pb.pbstatus_zh = ProductBrandStatus(pb.PBstatus).zh_value
                pb.add('pbstatus_zh')
        supplizer.fill('pbs', pbs)
        supplizer.fill('SUbaseRate', supplizer.SUbaseRate or 0)
        return Success(data=supplizer)

    def _fill_supplizer(self, supplizer):
        supplizer.hide('SUpassword')
        favor = UserWallet.query.filter(
            UserWallet.isdelete == False,
            UserWallet.USid == supplizer.SUid,
            UserWallet.CommisionFor == ApplyFrom.supplizer.value
        ).first()
        supplizer.fill('uwbalance', getattr(favor, 'UWbalance', 0))
        supplizer.fill('uwtotal', getattr(favor, 'UWtotal', 0))
        supplizer.fill('uwcash', getattr(favor, 'UWcash', 0))
        supplizer.fill('sustatus_zh', UserStatus(supplizer.SUstatus).zh_value)
        supplizer.fill('sustatus_en', UserStatus(supplizer.SUstatus).name)

    @admin_required
    def offshelves(self):
        current_app.logger.info('下架供应商')
        data = parameter_required(('suid',))
        suid = data.get('suid')
        with db.auto_commit():
            supplizer = Supplizer.query.filter(
                Supplizer.isdelete == False,
                Supplizer.SUid == suid
            ).first_('供应商不存在')
            supplizer.SUstatus = UserStatus.forbidden.value
            db.session.add(supplizer)
            BASEADMIN().create_action(AdminActionS.update.value, 'Supplizer', suid)
            # 供应商的品牌也下架
            brand_count = ProductBrand.query.filter(
                ProductBrand.isdelete == False,
                ProductBrand.PBstatus == ProductBrandStatus.upper.value,
                ProductBrand.SUid == suid
            ).update({
                'PBstatus': ProductBrandStatus.off_shelves.value
            })
            current_app.logger.info('共下架了 {}个品牌'.format(brand_count))
            # 供应商的商品下架
            products_count = Products.query.filter(
                Products.isdelete == False,
                Products.PRstatus != ProductStatus.off_shelves.value,
                Products.CreaterId == suid
            ).update({
                'PRstatus': ProductStatus.off_shelves.value,
            })
            current_app.logger.info('共下架了 {}个商品'.format(products_count))
        return Success('供应商下架成功')

    @admin_required
    def delete(self):
        """删除"""
        data = parameter_required(('suid',))
        suid = data.get('suid')
        with db.auto_commit():
            supplizer = Supplizer.query.filter(
                Supplizer.isdelete == False,
                Supplizer.SUid == suid
            ).first_('供应商不存在')
            if self._check_lasting_order(suid=suid):
                raise StatusError('供应商部分订单正在进行')

            supplizer.isdelete = True
            db.session.add(supplizer)
            BASEADMIN().create_action(AdminActionS.delete.value, 'Supplizer', suid)
            # 品牌删除
            productbrands = ProductBrand.query.filter(
                ProductBrand.isdelete == False,
                ProductBrand.SUid == suid
            ).all()
            current_app.logger.info('删除供应商{}'.format(supplizer.SUname))
            for pb in productbrands:
                pb.isdelete = True
                db.session.add(pb)
                # 商品删除
                delete_product = Products.query.filter(
                    Products.isdelete == False,
                    Products.PBid == pb.PBid
                ).update({
                    'PRstatus': ProductStatus.off_shelves.value
                })
        return Success('删除成功')

    def _check_lasting_order(self, **kwargs):
        """检查是否有进行中的订单"""
        suid = kwargs.get('suid')
        # 已付款但是未完成的正常订单
        nomal_order = OrderMain.query.filter(OrderMain.isdelete == False,
                                             OrderMain.PRcreateId == suid,
                                             OrderMain.OMinRefund == False,
                                             OrderMain.OMstatus.in_([OrderMainStatus.wait_send.value,
                                                                     OrderMainStatus.wait_recv.value,
                                                                     OrderMainStatus.wait_comment.value,
                                                                     OrderMainStatus.complete_comment.value
                                                                     ]))
        # 主订单在售后中
        refund_order = OrderMain.query.filter(OrderMain.isdelete == False,
                                              OrderMain.PRcreateId == suid,
                                              OrderMain.OMinRefund == True,
                                              OrderRefundApply.OMid == OrderMain.OMid,
                                              OrderRefundApply.isdelete == False,
                                              or_(OrderRefundApply.ORAstatus == ApplyStatus.wait_check.value,
                                                  and_(OrderRefundApply.ORAstatus == ApplyStatus.agree.value,
                                                       OrderRefundApply.ORAstate == OrderRefundORAstate.goods_money.value,
                                                       OrderRefund.ORAid == OrderRefundApply.ORAid,
                                                       OrderRefund.isdelete == False,
                                                       OrderRefund.ORstatus.in_([OrderRefundOrstatus.wait_send.value,
                                                                                 OrderRefundOrstatus.wait_recv.value,
                                                                                 OrderRefundOrstatus.ready_recv.value])))
                                              )
        # 附订单在收货中
        part_refund_order = OrderMain.query.filter(OrderPart.isdelete == False,
                                                   OrderPart.OMid == OrderMain.OMid,
                                                   OrderMain.isdelete == False,
                                                   OrderMain.PRcreateId == suid,
                                                   OrderPart.OPisinORA == True,
                                                   OrderRefundApply.OPid == OrderPart.OPid,
                                                   OrderRefundApply.isdelete == False,
                                                   or_(OrderRefundApply.ORAstatus == ApplyStatus.wait_check.value,
                                                       and_(OrderRefundApply.ORAstatus == ApplyStatus.agree.value,
                                                            OrderRefundApply.ORAstate == OrderRefundORAstate.goods_money.value,
                                                            OrderRefund.ORAid == OrderRefundApply.ORAid,
                                                            OrderRefund.isdelete == False,
                                                            OrderRefund.ORstatus.in_(
                                                                [OrderRefundOrstatus.wait_send.value,
                                                                 OrderRefundOrstatus.wait_recv.value,
                                                                 OrderRefundOrstatus.ready_recv.value])))
                                                   )
        lasting_order = nomal_order.union(refund_order).union(part_refund_order).all()
        return lasting_order

    @token_required
    def change_password(self):
        if not is_supplizer() and not is_admin():
            raise AuthorityError()
        form = SupplizerChangePasswordForm().valid_data()
        old_password = form.oldpassword.data
        supassword = form.supassword.data
        suid = form.suid.data
        with db.auto_commit():
            supplizer = Supplizer.query.filter(
                Supplizer.isdelete == False,
                Supplizer.SUid == suid
            ).first_('不存在的供应商')
            if not is_admin() and not check_password_hash(supplizer.SUpassword, old_password):
                raise AuthorityError('原密码错误')
            supplizer.SUpassword = generate_password_hash(supassword)
            db.session.add(supplizer)
            if is_admin():
                BASEADMIN().create_action(AdminActionS.update.value, 'Supplizer', suid)
        return Success('修改成功')

    @token_required
    def reset_password(self):
        form = SupplizerResetPasswordForm().valid_data()
        mobile = form.suloginphone.data
        password = form.supassword.data
        if is_supplizer():
            code = form.code.data
            correct_code = conn.get(mobile + '_code')
            if correct_code:
                correct_code = correct_code.decode()
            current_app.logger.info('correct code is {}, code is {}'.format(correct_code, code))
            if code != correct_code:
                raise ParamsError('验证码错误')
        if not is_admin():
            raise AuthorityError()
        with db.auto_commit():
            supplizer = Supplizer.query.filter(
                Supplizer.isdelete == False,
                Supplizer.SUloginPhone == mobile
            ).first()
            supplizer.update({
                'SUpassword': generate_password_hash(password)
            })
            db.session.add(supplizer)
            BASEADMIN().create_action(AdminActionS.update.value, 'Supplizer', supplizer.SUid)
        return Success('修改成功')

    @token_required
    def send_reset_password_code(self):
        """发送修改验证码"""
        if not is_supplizer():
            raise AuthorityError()
        form = SupplizerSendCodeForm().valid_data()
        mobile = form.suloginphone.data
        Supplizer.query.filter(
            Supplizer.isdelete == False,
            Supplizer.SUloginPhone == mobile
        ).first_('不存在的供应商')
        exist_code = conn.get(mobile + '_code')
        if exist_code:
            return DumpliError('重复发送')
        nums = [str(x) for x in range(10)]
        code = ''.join([random.choice(nums) for _ in range(6)])
        key = mobile + '_code'
        conn.set(key, code, ex=60)  # 60s过期
        params = {"code": code}
        app = current_app._get_current_object()
        send_task = Thread(target=self._async_send_code, args=(mobile, params, app), name='send_code')
        send_task.start()
        return Success('发送成功')

    def _async_send_code(self, mobile, params, app):
        with app.app_context():
            response_send_message = SendSMS(mobile, params)
            if not response_send_message:
                current_app.logger.error('发送失败')

    @get_session
    @token_required
    def set_supplizeraccount(self):
        if not is_supplizer():
            raise AuthorityError

        from flask import request
        from planet.control.CUser import CUser
        data = request.json
        cuser = CUser()
        cardno = data.get('sacardno')
        cardno = re.sub(r'\s', '', str(cardno))
        cuser._CUser__check_card_num(cardno)
        check_res = cuser._verify_cardnum(cardno)  # 检验卡号
        if not check_res.data.get('validated'):
            raise ParamsError('请输入正确的银行卡号')
        checked_res = cuser._verify_cardnum(data.get('sabankaccount'))
        # if not checked_res.data.get('validated'):
        #     raise ParamsError('请输入正确的开票账户银行卡号')
        checked_name = cuser._verify_chinese(data.get('sacardname'))
        if not checked_name or len(checked_name[0]) < 2:
            raise ParamsError('请输入正确的开户人姓名')
        current_app.logger.info('用户输入银行名为:{}'.format(data.get('sabankname')))
        bankname = check_res.data.get('cnbankname')
        try:
            WexinBankCode(bankname)
        except Exception:
            raise ParamsError('系统暂不支持该银行提现，请更换银行后重新保存')
        data['sabankname'] = bankname
        current_app.logger.info('校验后更改银行名为:{}'.format(data.get('sabankname')))

        sa = SupplizerAccount.query.filter(
            SupplizerAccount.SUid == request.user.id, SupplizerAccount.isdelete == False).first()
        if sa:
            for key in sa.__dict__:
                if str(key).lower() in data:
                    if re.match(r'^(said|suid)$', str(key).lower()):
                        continue
                    if str(key).lower() == 'sacardno':
                        setattr(sa, key, cardno)
                        continue
                    setattr(sa, key, data.get(str(key).lower()))
        else:
            sa_dict = {}
            for key in SupplizerAccount.__dict__:

                if str(key).lower() in data:
                    if not data.get(str(key).lower()):
                        continue
                    if str(key).lower() == 'suid':
                        continue
                    if str(key).lower() == 'sacardno':
                        sa_dict.setdefault(key, cardno)
                        continue
                    sa_dict.setdefault(key, data.get(str(key).lower()))
            sa_dict.setdefault('SAid', str(uuid.uuid1()))
            sa_dict.setdefault('SUid', request.user.id)
            sa = SupplizerAccount.create(sa_dict)
            db.session.add(sa)

        return Success('设置供应商账户信息成功')

    @token_required
    def get_supplizeraccount(self):

        from flask import request
        sa = SupplizerAccount.query.filter(
            SupplizerAccount.SUid == request.user.id, SupplizerAccount.isdelete == False).first()
        # if not sa:

        return Success('获取供应商账户信息成功', data=sa)

    @token_required
    def get_system_notes(self):
        if is_supplizer():
            mn_list = ManagerSystemNotes.query.filter(
                ManagerSystemNotes.MNstatus == NotesStatus.publish.value)
        elif is_admin():
            mn_list = ManagerSystemNotes.query.filter(ManagerSystemNotes.isdelete == False)
        else:
            raise AuthorityError

        mn_list = mn_list.order_by(ManagerSystemNotes.createtime.desc()).all()

        for mn in mn_list:
            mn.fill('mnstatus_zh', NotesStatus(mn.MNstatus).zh_value)
            mn.fill('mnstatus', NotesStatus(mn.MNstatus).name)

        return Success('获取通告成功', data=mn_list)

    @admin_required
    def add_update_notes(self):
        # 创建或更新通告
        from flask import request
        if not is_admin():
            raise AuthorityError
        data = parameter_required(('mncontent', 'mnstatus'))
        mnstatus = data.get('mnstatus')
        mnstatus = getattr(NotesStatus, mnstatus, None)
        if not mnstatus:
            mnstatus = 0
        else:
            mnstatus = mnstatus.value

        mncontent = data.get('mncontent')
        mnid = data.get('mnid')
        with db.auto_commit():
            if mnid:
                mn = ManagerSystemNotes.query.filter(
                    ManagerSystemNotes.MNid == mnid, ManagerSystemNotes.isdelete == False).first()
                if mn:
                    mn.MNcontent = mncontent
                    mn.MNstatus = mnstatus
                    mn.MNupdateid = request.user.id
                    return Success('更新通告成功', data=mn.MNid)

            mn = ManagerSystemNotes.create({
                'MNid': str(uuid.uuid1()),
                'MNcontent': mncontent,
                'MNstatus': mnstatus,
                'MNcreateid': request.user.id
            })

            db.session.add(mn)
            BASEADMIN().create_action(AdminActionS.insert.value, 'ManagerSystemNotes', str(uuid.uuid1()))
        return Success('创建通告成功', data=mn.MNid)

    @token_required
    def get_verifier(self):
        form = GetVerifier().valid_data()
        suid = form.suid.data
        if is_supplizer():
            suid = request.user.id
        if not suid:
            raise ParamsError('未指定供应商')
        tv_list = TicketVerifier.query.filter_by(SUid=suid, isdelete=False).order_by(
            TicketVerifier.TVphone.desc()).all_with_page()

        phone_list = [tv.TVphone for tv in tv_list]
        return Success(data=phone_list)

    @token_required
    def set_verifier(self):
        form = SetVerifier().valid_data()
        if is_admin():
            suid = form.suid.data
            assert suid, '供应商未指定'
        elif is_supplizer():
            suid = request.user.id
        else:
            raise AuthorityError()
        phone_list = form.phone_list.data
        tvid_list = []
        instence_list = []
        phone_list = {}.fromkeys(phone_list).keys()
        with db.auto_commit():
            for phone in phone_list:
                tv = TicketVerifier.query.filter_by(SUid=suid, TVphone=phone).first()
                if not tv:
                    tv = TicketVerifier.create({
                        'TVid': str(uuid.uuid1()),
                        'SUid': suid,
                        'TVphone': phone
                    })
                    instence_list.append(tv)
                tvid_list.append(tv.TVid)

            db.session.add_all(instence_list)
            # 删除无效的
            TicketVerifier.query.filter(
                TicketVerifier.isdelete == false(),
                TicketVerifier.SUid == suid,
                TicketVerifier.TVid.notin_(tvid_list)
            ).delete_(synchronize_session=False)
        return Success('修改成功',data=suid)
