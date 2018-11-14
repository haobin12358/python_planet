# -*- coding: utf-8 -*-
from datetime import datetime

from sqlalchemy import or_, not_

from planet.common.success_response import Success
from planet.common.token_handler import is_admin, token_required
from planet.extensions.validates.trade import CouponUserListForm
from planet.models import Items, User, ProductCategory, ProductBrand
from planet.models.trade import Coupon, CouponUser, CouponItem
from planet.service.STrade import STrade


class CCoupon(object):
    def __init__(self):
        self.strade = STrade()

    @token_required
    def list(self):
        """获取优惠券列表"""
        form = CouponUserListForm().valid_data()
        itid = form.itid.data
        coupons = Coupon.query
        if itid:
            coupons = coupons.join(CouponItem, CouponItem.COid == Coupon.COid).filter_(
                CouponItem.ITid == itid
            )
        coupons = coupons.all_with_page()
        for coupon in coupons:
            # 标签
            items = Items.query.join(CouponItem, CouponItem.ITid == Items.ITid).filter(
                CouponItem.COid == coupon.COid
            )
            coupon.fill('items', items)
        return Success(data=coupons)

    @token_required
    def list_user_coupon(self):
        """获取用户优惠券"""
        form = CouponUserListForm().valid_data()
        usid = form.usid.data
        itid = form.itid.data
        can_use = form.can_use.data  # 是否可用
        ucuserstatus = dict(form.ucuserstatus.choices).get(form.ucuserstatus.data)  # 是否已经使用
        user_coupon = CouponUser.query.filter_by_({'USid': usid}).filter_(
            CouponUser.UCalreadyUse == ucuserstatus
        )
        # 过滤标签
        if itid:
            user_coupon = user_coupon.join(CouponItem, CouponItem.COid == CouponUser.COid).filter_(CouponItem.ITid == itid)
        # 过滤是否可用
        time_now = datetime.now()
        if can_use:
            user_coupons = user_coupon.join(Coupon, Coupon.COid == CouponUser.COid).filter_(
                or_(Coupon.COvalieEndTime > time_now, Coupon.COvalieEndTime.is_(None)),
                or_(Coupon.COvalidStartTime < time_now, Coupon.COvalidStartTime.is_(None)),
                Coupon.COisAvailable == True,  # 可用
                CouponUser.UCalreadyUse == False  # 未用
            ).all_with_page()
        elif can_use is False:
            user_coupons = user_coupon.join(Coupon, Coupon.COid == CouponUser.COid).filter_(
                not(
                    or_(Coupon.COvalieEndTime > time_now, Coupon.COvalieEndTime.is_(None)),
                    or_(Coupon.COvalidStartTime < time_now, Coupon.COvalidStartTime.is_(None)),
                    Coupon.COisAvailable == True,
                    CouponUser.UCalreadyUse == False
                )
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
            coupon.subtitles = self._title_subtitle(coupon)
            coupon.fields = ['subtitles', 'COname', 'COisAvailable', 'COdiscount', 'COdownLine', 'COsubtration']
            user_coupon.fill('coupon', coupon)
            # 标签
            item = Items.query.join(CouponItem, CouponItem.ITid == Items.ITid).filter(
                CouponItem.COid == user_coupon.COid
            ).all()
            user_coupon.fill('item', item)
        return Success(data=user_coupons)

    def create(self):
        pass

    def update(self):
        pass

    @staticmethod
    def _title_subtitle(coupon):
        can_use = True
        if coupon.PCid:
            category = ProductCategory.query.filter_by_({'PCid': coupon.PCid}).first()
            title = '{}类专用'.format(category.PCname)
        elif coupon.pbid:
            brand = ProductBrand.query.filter_by_({'PBid': coupon.pbid}).first()
            title = '{}品牌专用'.format(brand.PBname)
        else:
            title = '全场通用'
        if coupon.COvalieEndTime or coupon.COvalieEndTime:
            subtitle = '限时优惠'
        else:
            subtitle = ''
        # 判断是否可用
        time_now = datetime.now()
        ended = (  # 已结束
            coupon.COvalieEndTime < time_now if coupon.COvalieEndTime else False
        )
        not_start = (  # 未开始
            coupon.COvalidStartTime > time_now if coupon.COvalidStartTim else False
        )
        if ended or not_start or not coupon.COisAvailable or coupon.UCalreadyUse:
            can_use = False
        return {
            'title': title,
            'subtitle': subtitle,
            'can_use': can_use
        }

