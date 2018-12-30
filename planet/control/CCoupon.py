# -*- coding: utf-8 -*-
import uuid
from datetime import datetime

from flask import request
from sqlalchemy import or_, and_

from planet.common.error_response import StatusError
from planet.common.params_validates import parameter_required
from planet.common.success_response import Success
from planet.common.token_handler import is_admin, token_required, is_tourist, admin_required
from planet.config.cfgsetting import ConfigSettings
from planet.config.enums import ItemType
from planet.extensions.register_ext import db
from planet.extensions.validates.trade import CouponUserListForm, CouponListForm, CouponCreateForm, CouponFetchForm, \
    CouponUpdateForm
from planet.models import Items, User, ProductCategory, ProductBrand, CouponFor, Products
from planet.models.trade import Coupon, CouponUser, CouponItem
from planet.service.STrade import STrade


class CCoupon(object):
    def __init__(self):
        self.strade = STrade()

    def list(self):
        """获取优惠券列表"""
        form = CouponListForm().valid_data()
        itid = form.itid.data
        coupons = Coupon.query
        usid = 'tourist' if is_tourist() else request.user.id
        if itid:
            coupons = coupons.join(CouponItem, CouponItem.COid == Coupon.COid).filter_(
                CouponItem.ITid == itid
            )
        coupons = coupons.order_by(Coupon.createtime.desc(), Coupon.COid).all_with_page()
        for coupon in coupons:
            # 标签
            items = Items.query.join(CouponItem, CouponItem.ITid == Items.ITid).filter(
                CouponItem.COid == coupon.COid
            ).all()
            # 优惠券时候对象
            coupon.fill('items', items)
            coupon.fill('title_subtitle', self._title_subtitle(coupon))
            coupon_user = CouponUser.query.filter_by_({'USid': usid, 'COid': coupon.COid}).first()
            coupon.fill('ready_collected', bool(coupon_user))
        return Success(data=coupons)

    @token_required
    def list_user_coupon(self):
        """获取用户优惠券"""
        form = CouponUserListForm().valid_data()
        usid = form.usid.data
        itid = form.itid.data
        can_use = dict(form.canuse.choices).get(form.canuse.data)   # 是否可用
        ucalreadyuse = dict(form.ucalreadyuse.choices).get(form.ucalreadyuse.data)  # 是否已经使用
        user_coupon = CouponUser.query.filter_by_({'USid': usid}).filter_(
            CouponUser.UCalreadyUse == ucalreadyuse
        )
        # 过滤标签
        if itid:
            user_coupon = user_coupon.join(CouponItem, CouponItem.COid == CouponUser.COid).filter_(CouponItem.ITid == itid)
        # 过滤是否可用
        time_now = datetime.now()
        if can_use:
            user_coupons = user_coupon.join(Coupon, Coupon.COid == CouponUser.COid).filter_(
                or_(Coupon.COvalidEndTime > time_now, Coupon.COvalidEndTime.is_(None)),
                or_(Coupon.COvalidStartTime < time_now, Coupon.COvalidStartTime.is_(None)),
                Coupon.COisAvailable == True,  # 可用
                # CouponUser.UCalreadyUse == False,  # 未用
            ).all_with_page()
        elif can_use is False:
            user_coupons = user_coupon.join(Coupon, Coupon.COid == CouponUser.COid).filter(
                or_(
                    Coupon.COisAvailable == False,
                    # CouponUser.UCalreadyUse == True,
                    Coupon.COvalidEndTime < time_now,   # 已经结束
                    # Coupon.COvalidStartTime > time_now ,  # 未开始
                ),

            ).all_with_page()
        else:
            user_coupons = user_coupon.all_with_page()
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

    @admin_required
    def create(self):
        form = CouponCreateForm().valid_data()
        pbids = form.pbids.data
        prids = form.prids.data
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
                'ADid': request.user.id
            })
            s_list.append(coupon_instance)
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
                coupon_for = CouponFor.create({
                    'CFid': str(uuid.uuid1()),
                    'PBid': pbid,
                    'COid': coupon_instance.COid,
                })
                s_list.append(coupon_for)
            for prid in prids:
                coupon_for = CouponFor.create({
                    'CFid': str(uuid.uuid1()),
                    'PRid': prid,
                    'COid': coupon_instance.COid,
                })
                s_list.append(coupon_for)
            s.add_all(s_list)
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
            coupon.update({
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
            }, 'dont ignore')
            db.session.add(coupon)
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
            CouponFor.query.filter(
                CouponFor.isdelete == False,
                CouponFor.COid == coid,
                and_(CouponFor.PBid.notin_(pbids),
                     CouponFor.PRid.notin_(prids))
            ).delete_(synchronize_session=False)
        return Success('修改成功')

    @admin_required
    def delete(self):
        data = parameter_required(('coid', ))
        coid = data.get('coid')
        with db.auto_commit():
            coupon = Coupon.query.filter(
                Coupon.isdelete == False,
                Coupon.COid == coid,
            ).first_('优惠券不存在')
            coupon.isdelete = True
            db.session.add(coupon)
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
            if coupon.COcollectNum and coupon_user_count > coupon.COcollectNum:
                raise StatusError('已经领取过')
            # 发放完毕或抢空
            if coupon.COlimitNum:
                # 共领取的数量
                if not coupon.COremainNum:
                    raise StatusError('来晚了')
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

    @staticmethod
    def _title_subtitle(coupon):
        # 使用对象限制
        coupon_fors = CouponFor.query.filter_by_({'COid': coupon.COid}).all()
        if len(coupon_fors) == 1:
            if coupon_fors[0].PCid:
                category = ProductCategory.query.filter_by_({'PCid': coupon_fors[0].PCid}).first()
                title = '{}类专用'.format(category.PCname)
                left_logo = category['PCpic']
                left_text = category.PCname
            elif coupon_fors[0].PBid:
                brand = ProductBrand.query.filter_by_({'PBid': coupon_fors[0].PBid}).first()
                title = '{}品牌专用'.format(brand.PBname)
                left_logo = brand['PBlogo']
                left_text = brand.PBname
                coupon.fill('brands', [brand])
            elif coupon_fors[0].PRid:
                product = Products.query.filter_by_({'PRid': coupon_fors[0].PRid}).first()
                title = '单品专用'.format(product.PRtitle)
                left_logo = product['PRmainpic']
                left_text = product.PRtitle
                coupon.fill('products', [product])
        elif coupon_fors:
            # 多品牌
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
                coupon.fill('brands', brands)
            # 多商品
            else:
                prids = [x.PRid for x in coupon_fors if x.PRid]
                left_logo = cfg.get_item('planet', 'logo')
                title = '多商品专用'
                for_product = []
                products = []
                for prid in prids:
                    product = Products.query.filter_by_({'PRid': prid}).first()
                    if product:
                        products.append(product)
                        for_product.append(product.PRtitle)
                left_text = '{}通用'.format('/'.join(for_product))
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
        return {
            'title': title,
            'subtitle': subtitle,
            'left_logo': left_logo,
            'left_text': left_text
        }

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

