# -*- coding: utf-8 -*-
import uuid
from datetime import datetime
from decimal import Decimal

from flask import request, current_app
from sqlalchemy import or_

from planet.common.error_response import StatusError, AuthorityError, ParamsError
from planet.common.params_validates import parameter_required
from planet.common.success_response import Success
from planet.common.token_handler import is_admin, token_required, is_tourist, admin_required, is_supplizer
from planet.config.cfgsetting import ConfigSettings
from planet.config.enums import ItemType, SupplizerDepositLogType, AdminAction, AdminActionS, CategoryType
from planet.control.BaseControl import BASEADMIN
from planet.extensions.register_ext import db
from planet.extensions.validates.trade import CouponUserListForm, CouponListForm, CouponCreateForm, CouponFetchForm, \
    CouponUpdateForm
from planet.models import Items, User, ProductCategory, ProductBrand, CouponFor, Products, Supplizer, \
    SupplizerDepositLog
from planet.models.trade import Coupon, CouponUser, CouponItem, CouponCode
from planet.service.STrade import STrade
import string
import random


class CCoupon(object):
    def __init__(self):
        self.strade = STrade()

    def list(self):
        """获取优惠券列表"""
        form = CouponListForm().valid_data()
        itid = form.itid.data
        coupons = Coupon.query.filter(
            Coupon.isdelete == False
        )
        usid = suid = adid = None
        if is_supplizer():
            suid = request.user.id
        elif is_admin():
            adid = request.user.id
        elif not is_tourist():
            usid = request.user.id
        if itid:
            coupons = coupons.join(CouponItem, CouponItem.COid == Coupon.COid).filter(
                CouponItem.ITid == itid,
                CouponItem.isdelete == False
            )

        if suid:
            coupons = coupons.filter(
                Coupon.SUid == suid
            )
        coupons = coupons.order_by(Coupon.createtime.desc(), Coupon.COid).all_with_page()
        return_coupons = list()
        for coupon in coupons:
            # 标签
            if itid and itid == 'home_recommend_category' and usid:
                coupon_user = CouponUser.query.filter(
                    CouponUser.isdelete == False,
                    CouponUser.COid == coupon.COid,
                    CouponUser.USid == usid
                ).first()
                if coupon_user:
                    current_app.logger.info('coupon_user ={}'.format(coupon_user))
                    continue
            self._coupon(coupon, usid=usid)

            return_coupons.append(coupon)
        return Success(data=return_coupons)

    def get(self):
        data = parameter_required(('coid',))
        coid = data.get('coid')
        coupon = Coupon.query.filter(
            Coupon.COid == coid,
            Coupon.isdelete == False,
        ).first()
        self._coupon(coupon)
        return Success(data=coupon)

    def _coupon(self, coupon, **kwargs):
        items = Items.query.join(CouponItem, CouponItem.ITid == Items.ITid).filter(
            CouponItem.COid == coupon.COid
        ).all()
        fill_con = kwargs.get('fill_con', True)
        if not is_admin() and not is_supplizer():
            coupon.COcanCollect = self._can_collect(coupon)
        # 优惠券使用对象
        if fill_con:
            coupon.fill('items', items)
        coupon.fill('title_subtitle', self._title_subtitle(coupon, fill_con))
        coupon.fill('cocode', bool(coupon.COcode))
        usid = kwargs.get('usid')
        if usid:
            coupon_user = CouponUser.query.filter_by({'USid': usid, 'COid': coupon.COid}).first()
            coupon.fill('ready_collected', bool(coupon_user))

    @token_required
    def list_user_coupon(self):
        """获取用户优惠券"""
        form = CouponUserListForm().valid_data()
        usid = form.usid.data
        itid = form.itid.data
        can_use = dict(form.canuse.choices).get(form.canuse.data)  # 是否可用
        ucalreadyuse = dict(form.ucalreadyuse.choices).get(form.ucalreadyuse.data)  # 是否已经使用
        user_coupon = CouponUser.query.filter(
            CouponUser.USid == usid,
            CouponUser.UCalreadyUse == ucalreadyuse,
            CouponUser.isdelete == False
        )
        # 过滤标签
        if itid:
            user_coupon = user_coupon.join(
                CouponItem, CouponItem.COid == CouponUser.COid
            ).filter(
                CouponItem.ITid == itid,
                CouponItem.isdelete == False)
        # 过滤是否可用
        user_coupon = user_coupon.join(Coupon, Coupon.COid == CouponUser.COid).filter(Coupon.isdelete == False)
        time_now = datetime.now()
        if can_use:
            user_coupons = user_coupon.filter_(
                or_(Coupon.COvalidEndTime > time_now, Coupon.COvalidEndTime.is_(None)),
                # or_(Coupon.COvalidStartTime < time_now, Coupon.COvalidStartTime.is_(None)),
                Coupon.COisAvailable == True,  # 可用
                # CouponUser.UCalreadyUse == False,  # 未用
            ).order_by(CouponUser.createtime.desc()).all_with_page()
        elif can_use is False:
            user_coupons = user_coupon.filter(
                or_(
                    Coupon.COisAvailable == False,
                    # CouponUser.UCalreadyUse == True,
                    Coupon.COvalidEndTime < time_now,  # 已经结束
                    # Coupon.COvalidStartTime > time_now ,  # 未开始
                ),

            ).order_by(CouponUser.createtime.desc()).all_with_page()
        else:
            user_coupons = user_coupon.order_by(CouponUser.createtime.desc()).all_with_page()
        for user_coupon in user_coupons:
            if is_admin():
                # 填用户
                user = User.query.filter(User.USid == user_coupon.USid).first()
                if user:
                    user.fields = ['USheader', 'USname', 'USid']
                user_coupon.fill('user', user)
            # 优惠券
            coupon = Coupon.query.filter(Coupon.COid == user_coupon.COid).first()  # 待优化
            coupon.title_subtitle = self._title_subtitle(coupon)
            # coupon.fields = ['title_subtitle', 'COname', 'COisAvailable', 'COdiscount', 'COdownLine', 'COsubtration']
            coupon.add('title_subtitle')
            user_coupon.fill('coupon', coupon)
            user_coupon.fill('can_use', self._isavalible(coupon, user_coupon))
            # 标签
            item = Items.query.join(CouponItem, CouponItem.ITid == Items.ITid).filter(
                CouponItem.COid == user_coupon.COid
            ).all()
            user_coupon.fill('item', item)
        return Success(data=user_coupons)

    def coupen_code(self):
        """生成兑换码"""
        lowercase = string.ascii_lowercase
        uppercase = string.ascii_uppercase
        digits = string.digits
        up_num = random.randint(0, 6)
        low_num = 6 - up_num
        code_list = []
        for i in range(low_num):
            code_list.append(random.choice(lowercase))
        for i in range(6):
            code_list.append(random.choice(digits))
        for i in range(up_num):
            code_list.append(random.choice(uppercase))
        code = ''
        code_list = random.sample(code_list, len(code_list))
        for i in range(len(code_list)):
            code += code_list[i]
        is_exists = CouponCode.query.filter_by_({
            'CCcode': code,
        }).first()
        if not is_exists:
            pass
        else:
            code = self.coupen_code()
        return code

    @token_required
    def create(self):
        form = CouponCreateForm().valid_data()
        pbids = form.pbids.data
        prids = form.prids.data
        adid = suid = None
        if is_admin():
            adid = request.user.id
        elif is_supplizer():
            suid = request.user.id
            """如果是供应商暂时取消发布折扣优惠券权限"""
            if form.codiscount.data != 10:
                raise ParamsError('暂不提供供应商发放折扣优惠券，请联系平台后台发放')
            if not form.colimitnum:
                raise ParamsError('需要指定发放数量')
            if not (pbids or prids):
                raise ParamsError('不能发放全平台优惠券')

        else:
            raise AuthorityError()
        with self.strade.auto_commit() as s:
            s_list = []
            coid = str(uuid.uuid1())
            itids = form.itids.data
            coupon_instance = Coupon.create({
                'COid': coid,
                'COname': form.coname.data,
                'COisAvailable': form.coisavailable.data,
                'COcanCollect': form.coiscancollect.data,
                'COlimitNum': form.colimitnum.data,
                'COcollectNum': form.cocollectnum.data,
                'COsendStarttime': form.cosendstarttime.data,
                'COsendEndtime': form.cosendendtime.data,
                'COvalidStartTime': form.covalidstarttime.data,
                'COvalidEndTime': form.covalidendtime.data,
                'COdiscount': form.codiscount.data,
                'COdownLine': form.codownline.data,
                'COsubtration': form.cosubtration.data,
                'COdesc': form.codesc.data,
                'COuseNum': form.cousenum.data,
                'ADid': adid,
                'SUid': suid,
                'COcode': form.cocode.data
            })
            s_list.append(coupon_instance)
            # # 是否要兑换码
            # if form.cocode.data == 1:
            #     ccid = str(uuid.uuid1())
            #     cccode = self.coupen_code()
            #     coupon_code = CouponCode.create({
            #         'CCid': ccid,
            #         'COid': coid,
            #         'CCcode': cccode
            #     })
            #     s_list.append(coupon_code)
            for itid in itids:
                s.query(Items).filter_by_({'ITid': itid, 'ITtype': ItemType.coupon.value}).first_('指定标签不存在')
                # 优惠券标签中间表
                couponitem_instance = CouponItem.create({
                    'CIid': str(uuid.uuid4()),
                    'COid': coid,
                    'ITid': itid
                })
                s_list.append(couponitem_instance)
            # 优惠券和应用对象的中间表
            for pbid in pbids:
                # 限制使用品牌
                pb = ProductBrand.query.filter(
                    ProductBrand.isdelete == False, ProductBrand.PBid == pbid, ProductBrand.SUid == suid).first_(
                    '品牌不存在')
                coupon_for = CouponFor.create({
                    'CFid': str(uuid.uuid1()),
                    'PBid': pbid,
                    'COid': coupon_instance.COid,
                })
                s_list.append(coupon_for)
            for prid in prids:
                # 限制使用商品
                if is_supplizer():
                    product = Products.query.filter(
                        Products.isdelete == False, Products.PRid == prid, Products.CreaterId == suid
                    ).first_('不能指定其他供应商商品')  # 0517 暂时取消管理员发放优惠券商品限制

                coupon_for = CouponFor.create({
                    'CFid': str(uuid.uuid1()),
                    'PRid': prid,
                    'COid': coupon_instance.COid,
                })
                s_list.append(coupon_for)

            if is_supplizer():
                # 供应商发放优惠券 押金扣除
                su = Supplizer.query.filter(Supplizer.isdelete == False, Supplizer.SUid == request.user.id).first()
                co_total = Decimal(str(coupon_instance.COlimitNum * coupon_instance.COsubtration))
                if su.SUdeposit < co_total:
                    raise ParamsError('供应商押金不足。当前账户剩余押金 {} 发放优惠券需要 {}'.format(su.SUdeposit, co_total))
                after_deposit = su.SUdeposit - co_total
                sdl = SupplizerDepositLog.create({
                    'SDLid': str(uuid.uuid1()),
                    'SUid': su.SUid,
                    'SDLnum': co_total,
                    # 'SDLtype': SupplizerDepositLogType.account_out.value,
                    'SDafter': after_deposit,
                    'SDbefore': su.SUdeposit,
                    'SDLacid': su.SUid
                })
                current_app.logger.info('供应商 {} 押金 {} 发放优惠券 {} 变更后 押金剩余 {} '.format(
                    su.SUname, su.SUdeposit, co_total, after_deposit
                ))
                su.SUdeposit = after_deposit
                s_list.append(sdl)

            # todo 优惠券历史创建
            s.add_all(s_list)
            if is_admin():
                BASEADMIN().create_action(AdminActionS.insert.value, 'Coupon', coid)
        return Success('添加成功', data=coid)

    @admin_required
    def update(self):
        form = CouponUpdateForm().valid_data()
        itids = form.itids.data
        coid = form.coid.data
        pbids = form.pbids.data
        prids = form.prids.data
        with db.auto_commit():
            coupon = Coupon.query.filter(
                Coupon.COid == coid,
                Coupon.isdelete == False
            ).first_('优惠券不存在')
            # 已经可以使用的不可以修改
            if coupon.COsendStarttime is None or coupon.COsendStarttime < datetime.now():
                raise StatusError('已经开放领取不可修改')
            coupon_dict = {
                'COname': form.coname.data,
                'COisAvailable': form.coisavailable.data,
                'COcanCollect': form.coiscancollect.data,
                'COlimitNum': form.colimitnum.data,
                'COcollectNum': form.cocollectnum.data,
                'COsendStarttime': form.cosendstarttime.data,
                'COsendEndtime': form.cosendendtime.data,
                'COvalidStartTime': form.covalidstarttime.data,
                'COvalidEndTime': form.covalidendtime.data,
                'COdiscount': form.codiscount.data,
                'COdownLine': form.codownline.data,
                'COsubtration': form.cosubtration.data,
                'COdesc': form.codesc.data,
                'COuseNum': form.cousenum.data,
                'COcode': form.cocode.data,
            }
            if form.colimitnum.data:
                coupon_dict.setdefault('COremainNum', form.colimitnum.data)
            coupon.update(coupon_dict, 'dont ignore')
            if coupon.SUid:
                # todo 如果修改的是供应商的优惠券。需要涉及押金的修改 目前不做校验
                pass

            db.session.add(coupon)
            BASEADMIN().create_action(AdminActionS.update.value, 'Coupon', coid)
            for itid in itids:
                Items.query.filter_by_({'ITid': itid, 'ITtype': ItemType.coupon.value}).first_('指定标签不存在')
                coupon_items = CouponItem.query.filter(CouponItem.ITid == itid, CouponItem.isdelete == False,
                                                       CouponItem.COid == coid).first()
                if not coupon_items:
                    # 优惠券标签中间表
                    couponitem_instance = CouponItem.create({
                        'CIid': str(uuid.uuid4()),
                        'COid': coupon.COid,
                        'ITid': itid
                    })
                    db.session.add(couponitem_instance)
            # 删除原有的标签
            CouponItem.query.filter(CouponItem.isdelete == False, CouponItem.ITid.notin_(itids),
                                    CouponItem.COid == coid).delete_(synchronize_session=False)
            # todo 修改此句
            CouponFor.query.filter(
                CouponFor.COid == coid,
                CouponFor.isdelete == False
            ).delete_(synchronize_session=False)
            # 优惠券和应用对象的中间表
            for pbid in pbids:
                coupon_for = CouponFor.create({
                    'CFid': str(uuid.uuid1()),
                    'PBid': pbid,
                    'COid': coid
                })
                db.session.add(coupon_for)
            for prid in prids:
                coupon_for = CouponFor.create({
                    'CFid': str(uuid.uuid1()),
                    'PRid': prid,
                    'COid': coid
                })
                db.session.add(coupon_for)
            # 删除无用的
            #
            # CouponFor.query.filter(
            #     CouponFor.isdelete == False,
            #     CouponFor.COid == coid,
            #     or_(CouponFor.PBid.notin_(pbids),
            #          CouponFor.PRid.notin_(prids))
            # ).delete_(synchronize_session=False)
        return Success('修改成功')

    @admin_required
    def delete(self):
        data = parameter_required(('coid',))
        coid = data.get('coid')
        with db.auto_commit():
            coupon = Coupon.query.filter(
                Coupon.isdelete == False,
                Coupon.COid == coid,
            ).first_('优惠券不存在')
            coupon.isdelete = True
            db.session.add(coupon)
            # 删除用户的优惠券
            coupon_user = CouponUser.query.filter(
                CouponUser.isdelete == False,
                CouponUser.COid == coid
            ).delete_()
            coupon_for = CouponFor.query.filter(
                CouponFor.isdelete == False,
                CouponFor.COid == coid
            ).delete_()
            BASEADMIN().create_action(AdminActionS.delete.value, 'CouponUser', coid)
            current_app.logger.info('删除优惠券的同时 将{}个用户拥有的优惠券也删除'.format(coupon_user))
        return Success('删除成功')

    @token_required
    def fetch(self):
        """领取优惠券"""
        form = CouponFetchForm().valid_data()
        coid = form.coid.data
        usid = request.user.id
        with self.strade.auto_commit() as s:
            s_list = []
            # 优惠券状态是否可领取
            coupon = s.query(Coupon).filter_by_({'COid': coid, 'COcanCollect': True}).first_('优惠券不存在或不可领取')
            coupon_user_count = s.query(CouponUser).filter_by_({'COid': coid, 'USid': usid}).count()
            # 领取过多
            if coupon.COcollectNum and coupon_user_count >= coupon.COcollectNum:
                raise StatusError('已经领取过')
            # 发放完毕或抢空
            if coupon.COlimitNum:
                # 共领取的数量
                if not coupon.COremainNum:
                    raise StatusError('已发放完毕')
                coupon.COremainNum = coupon.COremainNum - 1  # 剩余数量减1
                s_list.append(coupon)
            if coupon.COsendStarttime and coupon.COsendStarttime > datetime.now():
                raise StatusError('未开抢')
            if coupon.COsendEndtime and coupon.COsendEndtime < datetime.now():
                raise StatusError('来晚了')
            # 写入couponuser
            coupon_user_dict = {
                'UCid': str(uuid.uuid4()),
                'COid': coid,
                'USid': usid,
            }
            coupon_user_instance = CouponUser.create(coupon_user_dict)
            # 优惠券减1
            s_list.append(coupon_user_instance)
            s.add_all(s_list)
        return Success('领取成功')

    @token_required
    def code(self):
        """兑换码领优惠劵"""
        usid = request.user.id
        data = parameter_required(('cccode',))
        CCcode = data.get('cccode')
        with self.strade.auto_commit() as s:
            s_list = []
            couponcode = s.query(CouponCode).filter_by_({'CCcode': CCcode}).first_('兑换码不存在')
            if couponcode.CCused:
                raise ParamsError('兑换码已被使用')
            coid = couponcode.COid
            coupon = s.query(Coupon).filter_by_({'COid': coid}).first_()
            # 优惠券状态是否可领取
            coupon_user_count = s.query(CouponUser).filter_by_({'COid': coid, 'USid': usid}).count()
            # 领取过多
            if coupon.COcollectNum and coupon_user_count >= coupon.COcollectNum:
                raise StatusError('已经领取过')
            # 发放完毕或抢空
            # 2019-4-27 兑换码创建时保证库存
            # if coupon.COlimitNum:
            #     # 共领取的数量
            #     if not coupon.COremainNum:
            #         raise StatusError('已发放完毕')
            #     coupon.COremainNum = coupon.COremainNum - 1  # 剩余数量减1
            #     s_list.append(coupon)
            if coupon.COsendStarttime and coupon.COsendStarttime > datetime.now():
                raise StatusError('未开抢')
            if coupon.COsendEndtime and coupon.COsendEndtime < datetime.now():
                raise StatusError('来晚了')
            # 写入couponuser
            coupon_user_dict = {
                'UCid': str(uuid.uuid4()),
                'COid': coid,
                'USid': usid,
            }
            coupon_user_instance = CouponUser.create(coupon_user_dict)
            # 优惠券减1
            s_list.append(coupon_user_instance)
            s.add_all(s_list)
        return Success('领取成功')

    @staticmethod
    def _title_subtitle(coupon, fill_con=True):
        # 使用对象限制
        coupon_fors = CouponFor.query.filter_by_({'COid': coupon.COid}).all()
        coupon_type = CategoryType.green.value
        if len(coupon_fors) == 1:
            if coupon_fors[0].PCid:
                category = ProductCategory.query.filter_by_({'PCid': coupon_fors[0].PCid}).first()
                title = '{}类专用'.format(category.PCname)
                left_logo = category['PCpic']
                left_text = category.PCname
            elif coupon_fors[0].PBid:
                coupon_type = CategoryType.black.value
                brand = ProductBrand.query.filter_by_({'PBid': coupon_fors[0].PBid}).first()
                title = '{}品牌专用'.format(brand.PBname)
                left_logo = brand['PBlogo']
                left_text = brand.PBname
                if fill_con:
                    coupon.fill('brands', [brand])
            elif coupon_fors[0].PRid:
                coupon_type = CategoryType.black.value
                product = Products.query.filter(Products.PRid == coupon_fors[0].PRid).first()
                brand = ProductBrand.query.filter(ProductBrand.PBid == product.PBid).first()
                if fill_con:
                    product.fill('brand', brand)
                title = '单品专用'.format(product.PRtitle)
                left_logo = product['PRmainpic']
                left_text = product.PRtitle
                if fill_con:

                    coupon.fill('products', [product])
        elif coupon_fors:
            # 多品牌
            coupon_type = CategoryType.black.value
            cfg = ConfigSettings()
            pbids = [x.PBid for x in coupon_fors if x.PBid]
            left_logo = cfg.get_item('planet', 'logo')
            if pbids:
                title = '多品牌专用'
                for_brand = []
                brands = []
                for pbid in pbids:
                    brand = ProductBrand.query.filter(ProductBrand.PBid == pbid).first()
                    if brand:
                        brands.append(brand)
                        for_brand.append(brand.PBname)
                left_text = '{}通用'.format('/'.join(for_brand))
                if fill_con:
                    coupon.fill('brands', brands)
            # 多商品
            else:
                prids = [x.PRid for x in coupon_fors if x.PRid]
                left_logo = cfg.get_item('planet', 'logo')
                title = '多商品专用'
                for_product = []
                products = []
                for prid in prids:
                    product = Products.query.filter(Products.PRid == prid).first()
                    brand = ProductBrand.query.filter(ProductBrand.PBid == product.PBid).first()
                    if fill_con:
                        product.fill('brand', brand)
                    if product:
                        products.append(product)
                        for_product.append(product.PRtitle)
                left_text = '{}通用'.format('/'.join(for_product))
                if fill_con:
                    coupon.fill('products', products)
            # 多类目 暂时没有多类目优惠券
            pass
        else:
            title = '全场通用'
            cfg = ConfigSettings()
            left_logo = cfg.get_item('planet', 'logo')
            left_text = cfg.get_item('planet', 'title')
        # 使用下限
        if coupon.COdownLine:
            subtitle = '满{:g}元'.format(coupon.COdownLine)
        else:
            subtitle = '无限制'
        # 叠加方式
        if coupon.COuseNum:
            subtitle += '可用'
        else:
            subtitle += '可叠加'

        if coupon.COdiscount and coupon.COdiscount != 10:
            coupon_type = CategoryType.orange.value

        return {
            'coupon_type': coupon_type,
            'title': title,
            'subtitle': subtitle,
            'left_logo': left_logo,
            'left_text': left_text
        }

    def _can_collect(self, coupon):
        # 发放完毕或抢空
        can_not_collect = (not coupon.COcanCollect) or (coupon.COlimitNum and not coupon.COremainNum) or (
                coupon.COsendStarttime and coupon.COsendStarttime > datetime.now()) or (
                                  coupon.COsendEndtime and coupon.COsendEndtime < datetime.now())
        return not can_not_collect

    def _isavalible(self, coupon, user_coupon=None):
        # 判断是否可用
        time_now = datetime.now()
        ended = (  # 已结束
            coupon.COvalidEndTime < time_now if coupon.COvalidEndTime else False
        )
        not_start = (  # 未开始
            coupon.COvalidStartTime > time_now if coupon.COvalidStartTime else False
        )

        if user_coupon:
            avalible = not ended and not not_start and coupon.COisAvailable and not user_coupon.UCalreadyUse

        else:
            avalible = not (ended or not_start or not coupon.COisAvailable)
        return avalible

    @admin_required
    def create_code(self):
        data = parameter_required(('coid', 'conum'))
        coid = data.get('coid')
        conum = data.get('conum')
        with db.auto_commit():
            coupon = Coupon.query.filter_by(COid=coid, isdelete=False, COcode=1).first_('该优惠券不能生成兑换码')
            # 校验剩余数量
            if coupon.COlimitNum:
                if int(coupon.COremainNum) < int(conum):
                    raise StatusError('兑换数量超过剩余数量')
                coupon.update({'COremainNum': int(coupon.COremainNum) - int(conum)})
            # isinstance_list = [coupon]
            db.session.add(coupon)
            for _ in range(int(data.get('conum'))):
                ccid = str(uuid.uuid1())
                cccode = self.coupen_code()
                coupon_code = CouponCode.create({
                    'CCid': ccid,
                    'COid': coid,
                    'CCcode': cccode
                })
                db.session.add(coupon_code)
                BASEADMIN().create_action(AdminActionS.insert.value, 'CouponCode', coid)
                db.session.flush()

        return Success('生成激活码成功', data={'coid': coid, 'conum': conum})

    @admin_required
    def get_code_list(self):
        data = parameter_required(('coid',))
        coid = data.get('coid')
        cc_query = CouponCode.query.filter(CouponCode.COid == coid, CouponCode.isdelete == False)
        cc_all_count = cc_query.count()
        cc_used_count = cc_query.filter(CouponCode.CCused == True).count()
        cc_list = cc_query.all_with_page()
        return Success(data={'count': cc_all_count, 'used_count': cc_used_count, 'code': cc_list})

    @admin_required
    def update_code(self):
        data = parameter_required(('coid', 'cocode'))
        coupon = Coupon.query.filter_by(COid=data.get('coid'), isdelete=False).first_('优惠券已删除')

        with db.auto_commit():
            coupon.update({'COcode': bool(data.get('cocode', False))})
            BASEADMIN().create_action(AdminActionS.update.value, 'Coupon', data.get('coid'))

        return Success('修改成功', data={'coid': coupon.COid})
