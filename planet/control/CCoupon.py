# -*- coding: utf-8 -*-
import uuid
from datetime import datetime

from flask import request
from sqlalchemy import or_

from planet.common.error_response import StatusError
from planet.common.success_response import Success
from planet.common.token_handler import is_admin, token_required
from planet.config.cfgsetting import ConfigSettings
from planet.config.enums import ItemType
from planet.extensions.validates.trade import CouponUserListForm, CouponListForm, CouponCreateForm, CouponFetchForm
from planet.models import Items, User, ProductCategory, ProductBrand
from planet.models.trade import Coupon, CouponUser, CouponItem
from planet.service.STrade import STrade


class CCoupon(object):
    def __init__(self):
        self.strade = STrade()

    @token_required
    def list(self):
        """获取优惠券列表"""
        form = CouponListForm().valid_data()
        itid = form.itid.data
        coupons = Coupon.query
        usid = request.user.id
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

    def create(self):
        form = CouponCreateForm().valid_data()
        with self.strade.auto_commit() as s:
            s_list = []
            coid = str(uuid.uuid4())
            itids = form.itids.data
            coupon_instance = Coupon.create({
                'COid': coid,
                'PCid': form.pcid.data,
                'PRid': form.prid.data,
                'PBid': form.pbid.data,
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
            s.add_all(s_list)
        return Success('添加成功')

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


    def update(self):
        pass

    @staticmethod
    def _title_subtitle(coupon):
        # 使用对象限制
        if coupon.PCid:
            category = ProductCategory.query.filter_by_({'PCid': coupon.PCid}).first()
            title = '{}类专用'.format(category.PCname)
            left_logo = category['PCpic']
            left_text = category.PCname
        elif coupon.PBid:
            brand = ProductBrand.query.filter_by_({'PBid': coupon.PBid}).first()
            title = '{}品牌专用'.format(brand.PBname)
            left_logo = brand['PBlogo']
            left_text = brand.PBname
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

