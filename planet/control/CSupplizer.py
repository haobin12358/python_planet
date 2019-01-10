import random
import re
import uuid
import json
from threading import Thread
from flask import current_app
from werkzeug.security import generate_password_hash, check_password_hash

from planet.common.Inforsend import SendSMS
from planet.common.base_service import get_session
from planet.common.error_response import AuthorityError, ParamsError, DumpliError, NotFound
from planet.common.params_validates import parameter_required
from planet.common.success_response import Success
from planet.common.token_handler import admin_required, is_admin, is_supplizer, token_required
from planet.config.enums import ProductBrandStatus, UserStatus, ProductStatus, ApplyFrom
from planet.extensions.register_ext import db, conn
from planet.extensions.validates.user import SupplizerListForm, SupplizerCreateForm, SupplizerGetForm, \
    SupplizerUpdateForm, SupplizerSendCodeForm, SupplizerResetPasswordForm, SupplizerChangePasswordForm
from planet.models import Supplizer, ProductBrand, Products, UserWallet, SupplizerAccount


class CSupplizer:
    def __init__(self):
        pass

    @admin_required
    def list(self):
        """供应商列表"""
        form = SupplizerListForm().valid_data()
        kw = form.kw.data
        mobile = form.mobile.data

        supplizers = Supplizer.query.filter_by_().filter_(
            Supplizer.SUname.contains(kw),
            Supplizer.SUlinkPhone.contains(mobile)
        ).all_with_page()
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
            supplizer.fill('UWbalance', getattr(favor, 'UWbalance', 0))
            supplizer.fill('UWtotal', getattr(favor, 'UWtotal', 0))
            supplizer.fill('UWcash', getattr(favor, 'UWcash', 0))
        return Success(data=supplizers)

    @admin_required
    def create(self):
        """添加"""
        form = SupplizerCreateForm().valid_data()
        pbids = form.pbids.data
        with db.auto_commit():
            supperlizer = Supplizer.create({
                'SUid': str(uuid.uuid1()),
                'SUlinkPhone': form.sulinkphone.data,
                'SUloginPhone': form.suloginphone.data,
                'SUname': form.suname.data,
                'SUlinkman': form.sulinkman.data,
                'SUaddress': form.suaddress.data,
                'SUbanksn': form.subanksn.data,
                'SUbankname': form.subankname.data,
                'SUpassword': generate_password_hash(form.supassword.data),
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
            })
            db.session.add(supperlizer)
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
        return Success('创建成功', data={'suid': supperlizer.SUid})

    def update(self):
        """更新供应商信息"""
        if not is_admin() and not is_supplizer():
            raise AuthorityError()
        form = SupplizerUpdateForm().valid_data()
        pbids = form.pbids.data
        with db.auto_commit():
            supplizer = Supplizer.query.filter(
                Supplizer.isdelete == False,
                Supplizer.SUid == form.suid.data
            ).first_('供应商不存在')
            supplizer.update({
                'SUlinkPhone': form.sulinkphone.data,
                'SUname': form.suname.data,
                'SUlinkman': form.sulinkman.data,
                'SUaddress': form.suaddress.data,
                'SUbanksn': form.subanksn.data,
                'SUbankname': form.subankname.data,
                # 'SUpassword': generate_password_hash(form.supassword.data),  # todo 是不是要加上
                'SUheader': form.suheader.data,
                'SUcontract': form.sucontract.data,
                'SUemail': form.suemail.data,
            }, null='dont ignore')
            db.session.add(supplizer)
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
        return Success(data=supplizer)

    def _fill_supplizer(self, supplizer):
        supplizer.hide('SUpassword')
        favor = UserWallet.query.filter(
            UserWallet.isdelete == False,
            UserWallet.USid == supplizer.SUid,
            UserWallet.CommisionFor == ApplyFrom.supplizer.value
        ).first()
        supplizer.fill('UWbalance', getattr(favor, 'UWbalance', 0))
        supplizer.fill('UWtotal', getattr(favor, 'UWtotal', 0))
        supplizer.fill('UWcash', getattr(favor, 'UWcash', 0))


    @admin_required
    def offshelves(self):
        current_app.logger.info('下架供应商')
        data = parameter_required(('suid', ))
        suid = data.get('suid')
        with db.auto_commit():
            supplizer = Supplizer.query.filter(
                Supplizer.isdelete == False,
                Supplizer.SUid == suid
            ).first_('供应商不存在')
            supplizer.SUstatus = UserStatus.forbidden.value
            db.session.add(supplizer)
            # 供应商的品牌也下架
            brand_count = ProductBrand.query.filter(
                ProductBrand.isdelete == False,
                ProductBrand.PBstatus == ProductBrandStatus.upper.value,
                ProductBrand.SUid == suid
            ).update({
                'PBstatus':  ProductBrandStatus.off_shelves.value
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
        data = parameter_required(('suid', ))
        suid = data.get('suid')
        with db.auto_commit():
            supplizer = Supplizer.query.filter(
                Supplizer.isdelete == False,
                Supplizer.SUid == suid
            ).first_('供应商不存在')
            supplizer.isdelete = True
            db.session.add(supplizer)
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
            Supplizer.query.filter(
                Supplizer.isdelete == False,
                Supplizer.SUloginPhone == mobile
            ).update({
                'SUpassword': generate_password_hash(password)
            })
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
        data = request.json
        # todo 数据校验
        sa = SupplizerAccount.query.filter(
            SupplizerAccount.SUid == request.user.id, SupplizerAccount.isdelete == False).first()

        if sa:
            for key in sa.__dict__:
                if str(key).lower() in data:
                    if str(key).lower() == 'suid':
                        continue
                    setattr(sa, key, data.get(str(key).lower()))
        else:
            sa_dict = {}
            for key in SupplizerAccount.__dict__:

                if str(key).lower() in data:
                    if str(key).lower() == 'suid':
                        continue
                    if not data.get(str(key).lower()):
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
