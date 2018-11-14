# -*- coding: utf-8 -*-
from datetime import datetime

from planet.common.success_response import Success
from planet.common.token_handler import is_admin, token_required
from planet.extensions.validates.trade import CouponListForm
from planet.models import Items, User, ProductCategory, ProductBrand
from planet.models.trade import Coupon, CouponUser, CouponItem
from planet.service.STrade import STrade


class CCoupon(object):
    def __init__(self):
        self.strade = STrade()

    @token_required
    def list(self):
        pass

    @token_required
    def list_user_coupon(self):
        """获取用户优惠券"""
        form = CouponListForm().valid_data()
        usid = form.usid.data
        itid = form.itid.data
        user_coupon = CouponUser.query.filter_by_({'USid': usid})
        if itid:
            user_coupon = user_coupon.join(CouponItem, CouponItem.COid == CouponUser.COid).filter_(CouponItem.ITid == itid)
        user_coupons = user_coupon.all_with_page()
        for user_coupon in user_coupons:
            # 填用户
            if is_admin():
                user = User.query.filter(User.USid == user_coupon.USid).first()
                if user:
                    user.fields = ['USheader', 'USname', 'USid']
                user_coupon.fill('user', user)
            # 优惠券
            coupon = Coupon.query.filter(Coupon.COid == user_coupon.COid).first()
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
        if coupon.COvalieEndTime:
            time_now = datetime.now()
            if coupon.COvalieEndTime < time_now:
                can_use = False
            subtitle = '限时优惠'
        else:
            subtitle = ''
        if not coupon.COisAvailable:
            can_use = False
        return {
            'title': title,
            'subtitle': subtitle,
            'can_use': can_use
        }

