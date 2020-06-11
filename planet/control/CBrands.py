# -*- coding: utf-8 -*-
import json
import uuid

from flask import current_app
from qiniu import Auth
from sqlalchemy import or_, false

from planet.common.error_response import AuthorityError
from planet.common.params_validates import parameter_required
from planet.config.enums import ProductBrandStatus, ProductStatus, ItemType, AdminAction, AdminActionS, CategoryType
from planet.control.BaseControl import BASEADMIN
from planet.extensions.register_ext import db
from planet.service.SProduct import SProducts
from planet.models import ProductBrand, Products, Items, BrandWithItems, Supplizer, ProductItems, BrandBanner, Coupon, \
    CouponItem, CouponUser, CouponFor
from planet.common.success_response import Success
from planet.common.token_handler import token_required, is_supplizer, is_admin, admin_required, common_user, \
    get_current_user, get_current_supplizer
from planet.extensions.validates.product import BrandsListForm, BrandsCreateForm, BrandUpdateForm, request, ParamsError


class CBrands(object):
    def __init__(self):
        self.sproduct = SProducts()
        self.itid_re_pr = 'home_recommend'
        self.itid_re_ca = 'home_recommend_category'
        self.prfields = ['PRprice', 'PRtitle', 'PRmainpic', 'PRlinePrice', 'PRid']
        self.br_new = 5

    @token_required
    def create(self):
        """创建品牌"""
        data = BrandsCreateForm().valid_data()
        pblogo = data.pblogo.data
        pbname = data.pbname.data
        pbdesc = data.pbdesc.data
        pblinks = data.pblinks.data
        itids = data.itids.data
        suid = data.suid.data
        pbbackgroud = data.pbbackgroud.data
        pbsort = data.pbsort.data
        with self.sproduct.auto_commit() as s:
            s_list = []
            pbid = str(uuid.uuid1())
            pbsort = self._check_sort(pbsort, model=ProductBrand, default=1)
            pb_dict = {
                'PBid': pbid,
                'PBlogo': pblogo,
                'PBname': pbname,
                'PBdesc': pbdesc,
                'PBlinks': pblinks,
                'PBbackgroud': pbbackgroud,
                'PBsort': pbsort,
                'SUid': suid,
                'PBintegralPayRate': data.pbintegralpayrate.data
            }
            pb_instance = ProductBrand.create(pb_dict)
            s_list.append(pb_instance)
            # 创建标签-品牌中间表
            if itids:
                for itid in itids:
                    s.query(Items).filter_by_({'ITid': itid, 'ITtype': ItemType.brand.value}).first_(
                        '{}标签不存在或类型不正确'.format(itid))
                    brand_with_pbitem_instance = BrandWithItems.create({
                        'BWIid': str(uuid.uuid4()),
                        'ITid': itid,
                        'PBid': pbid
                    })
                    s_list.append(brand_with_pbitem_instance)

            s.add_all(s_list)
        return Success('添加成功', {'pbid': pb_instance.PBid})

    def list(self):
        form = BrandsListForm().valid_data()
        pbstatus = dict(form.pbstatus.choices).get(form.pbstatus.data)
        free = dict(form.free.choices).get(form.free.data)
        # time_order = dict(form.time_order.choices).get(form.time_order.data)
        itid = form.itid.data
        itid = itid.split('|') if itid else []
        kw = form.kw.data
        brand_query = ProductBrand.query.filter_(
            ProductBrand.isdelete == False,
            ProductBrand.PBstatus == pbstatus
        )
        if itid:
            brand_query = brand_query.join(
                BrandWithItems, ProductBrand.PBid == BrandWithItems.PBid
            ).filter(
                BrandWithItems.isdelete == False,
                BrandWithItems.ITid.in_(itid)
            )
        if is_supplizer():
            current_app.logger.info('供应商查看品牌列表..')
            brand_query = brand_query.filter(
                ProductBrand.SUid == request.user.id
            )
        if free is True:
            brand_query = brand_query.filter(
                ProductBrand.SUid.is_(None)
            )
        elif free is False:
            brand_query = brand_query.filter(
                ProductBrand.SUid.isnot(None)
            )
        if kw:
            brand_query = brand_query.filter(
                ProductBrand.PBname.contains(kw)
            )
        brands = brand_query.order_by(ProductBrand.PBsort.asc(), ProductBrand.createtime.desc()).all_with_page()

        for brand in brands:
            brand.fill('PBstatus_en', ProductBrandStatus(brand.PBstatus).name)
            brand.fill('PBstatus_zh', ProductBrandStatus(brand.PBstatus).zh_value)
            brand.add('createtime')
            # 标签
            print(brand.PBid)
            pb_items = Items.query.filter_by().join(BrandWithItems, Items.ITid == BrandWithItems.ITid).filter_(
                BrandWithItems.PBid == brand.PBid,
                BrandWithItems.isdelete == False,
            ).all()
            brand.fill('items', pb_items)
            if is_admin() or brand.SUid:
                supplizer = Supplizer.query.filter(
                    Supplizer.isdelete == False,
                    Supplizer.SUid == brand.SUid
                ).first()
                if not supplizer:
                    with db.auto_commit():
                        brand.SUid = None
                        db.session.add(brand)
                    continue
                supplizer.fields = ['SUloginPhone', 'SUlinkPhone', 'SUname', 'SUlinkman', 'SUheader']
                brand.fill('supplizer', supplizer)
            self._fill_brand(brand, recommend_pr=True, coupon=True)

        return Success(data=brands)

    def get(self):
        data = parameter_required(('pbid',))
        pbid = data.get('pbid')
        product_brand = ProductBrand.query.filter_by({'PBid': pbid}).first_('品牌不存在')
        product_brand.fill('pbstatus_en', ProductStatus(product_brand.PBstatus).name)
        self._fill_brand(product_brand, new_product=True, banner_show=True)
        return Success(data=product_brand)

    def list_with_group(self):
        form = BrandsListForm().valid_data()
        time_order = dict(form.time_order.choices).get(form.time_order.data)
        pbstatus = dict(form.pbstatus.choices).get(form.pbstatus.data)
        itid = form.itid.data
        if not itid:
            # todo 默认不会展示首页标签
            pass
        itid = itid.split('|') if itid else []
        print(itid)
        with self.sproduct.auto_commit() as s:
            items = s.query(Items).filter_(
                Items.ITtype == ItemType.brand.value,
                Items.ITid.in_(itid)
            ).filter_by_().order_by(Items.ITsort).all_(True)
            res = []
            for item in items:
                itid = item.ITid
                brands = self._get_brand_list(s, itid, pbstatus, time_order, page=False, pb_in_sub=False)
                if not brands:
                    continue
                item.fill('brands', brands)
                res.append(item)
        return Success(data=res)

    @token_required
    def off_shelves(self):
        """上下架"""
        data = parameter_required(('pbid',))
        pbid = data.get('pbid')
        pbstatus = data.get('pbstatus', 'up')
        with self.sproduct.auto_commit() as s:
            product_brand_instance = s.query(ProductBrand).filter_by_({
                'PBid': pbid
            }).first_('品牌不存在')
            s_list = []
            if pbstatus == 'up':
                # 上架
                product_brand_instance.PBstatus = ProductBrandStatus.upper.value
                s_list.append(product_brand_instance)
                msg = '上架成功'
            else:
                # 下架品牌
                product_brand_instance.PBstatus = ProductBrandStatus.off_shelves.value
                s_list.append(product_brand_instance)
                # 下架商品
                s.query(Products).filter_by_({'PBid': pbid}).update({
                    'PRstatus': ProductStatus.off_shelves.value
                })
                msg = '下架成功'
            s.add_all(s_list)
        return Success(msg)

    @token_required
    def update(self):
        data = BrandUpdateForm().valid_data()
        pblogo = data.pblogo.data
        pbname = data.pbname.data
        pbdesc = data.pbdesc.data
        pblinks = data.pblinks.data
        itids = data.itids.data
        suid = data.suid.data
        pbbackgroud = data.pbbackgroud.data
        pbid = data.pbid.data
        pbsort = data.pbsort.data

        with self.sproduct.auto_commit() as s:
            s_list = []
            product_brand_instance = s.query(ProductBrand).filter_by_({
                'PBid': pbid
            }).first_('不存在的品牌')
            if pbsort:
                pbsort = self._check_sort(pbsort, model=ProductBrand)
            else:
                pbsort = None
            product_brand_instance.update({
                'PBlogo': pblogo,
                'PBname': pbname,
                'PBdesc': pbdesc,
                'PBlinks': pblinks,
                'PBbackgroud': pbbackgroud,
                'SUid': suid,
                'PBsort': pbsort,
                'PBintegralPayRate': data.pbintegralpayrate.data
            })
            s_list.append(product_brand_instance)
            # 品牌已经关联的中间
            old_item_id = s.query(BrandWithItems.ITid).filter_by_({'PBid': pbid}).all()
            old_item_id = [x.ITid for x in old_item_id]
            if itids:
                for itid in itids:
                    if itid in old_item_id:
                        old_item_id.remove(itid)
                        # 已经存在
                        continue
                    # 如果没在之前的表中
                    else:
                        s.query(Items).filter_by_({'ITid': itid, 'ITtype': ItemType.brand.value}).first_(
                            '{}标签不存在或类型不正确'.format(itid))
                        brand_with_pbitem_instance = BrandWithItems.create({
                            'BWIid': str(uuid.uuid4()),
                            'ITid': itid,
                            'PBid': pbid
                        })
                        s_list.append(brand_with_pbitem_instance)
                # 删除
                s.query(BrandWithItems).filter_(BrandWithItems.ITid.notin_(itids),
                                                BrandWithItems.PBid == pbid,
                                                BrandWithItems.isdelete == False).delete_(synchronize_session=False)
            s.add_all(s_list)
        return Success('更新成功')

    @admin_required
    def delete(self):
        # todo 记录删除操作管理员
        data = parameter_required(('pbid',))
        pbid = data.get('pbid')
        with db.auto_commit():
            brand = ProductBrand.query.filter(
                ProductBrand.PBid == pbid,
                ProductBrand.isdelete == False
            ).first_('品牌不存在')
            brand.isdelete = True
            db.session.add(brand)
            BASEADMIN().create_action(AdminActionS.delete.value, 'ProductBrand', pbid)
            # 商品下架
            off_products = Products.query.filter(
                Products.isdelete == False,
                Products.PBid == pbid
            ).update({
                'PRstatus': ProductStatus.off_shelves.value
            })
        return Success('删除成功')

    def _get_brand_list(self, s, itid, pbstatus, time_order=(), pb_in_sub=True, page=True):
        itid = itid.split('|') if itid else []
        print(itid)
        brands = s.query(ProductBrand).filter_by_(). \
            outerjoin(BrandWithItems, ProductBrand.PBid == BrandWithItems.PBid). \
            filter_(
            or_(BrandWithItems.isdelete == False, BrandWithItems.isdelete.is_(None)),
            BrandWithItems.ITid.in_(itid),
            ProductBrand.PBstatus == pbstatus,
        ).order_by(ProductBrand.createtime).all_(page)
        for brand in brands:
            brand.fill('PBstatus_en', ProductBrandStatus(brand.PBstatus).name)
            brand.fill('PBstatus_zh', ProductBrandStatus(brand.PBstatus).zh_value)
            # 标签
            pb_items = s.query(Items).filter_by().join(BrandWithItems, Items.ITid == BrandWithItems.ITid).filter_(
                BrandWithItems.PBid == brand.PBid,
                BrandWithItems.isdelete == False,
            ).all()
            if pb_in_sub:
                brand.fill('pb_items', pb_items)
        return brands

    def _fill_brand(self, brand, **kwargs):
        product_num, product_fields, = kwargs.get('product_num', 3), kwargs.get('product_fields', list())
        new_product = kwargs.get('new_product', False)
        banner_show = kwargs.get('banner_show', False)
        recommend_pr = kwargs.get('recommend_pr', False)
        coupon = kwargs.get('coupon', False)

        if not product_fields:
            product_fields = self.prfields[:]

        if coupon:
            user = None
            if common_user():
                user = get_current_user()
            brand_coupon = self._get_brand_coupon(brand.SUid, user)

            if brand_coupon:
                from planet.control.CCoupon import CCoupon
                ccoupon = CCoupon()
                usid = user.USid if user else None
                ccoupon._coupon(brand_coupon, usid=usid, fill_con=False)
                product_num -= 1

                brand.fill('coupon', brand_coupon)

        # 推荐商品
        if recommend_pr:
            brand_recommend_product = self._recommend_pb_product(brand.PBid).all()[:product_num]
            pr_supplement_id = list()
            if brand_recommend_product:
                for product in brand_recommend_product:
                    product.fields = product_fields
                    pr_supplement_id.append(product.PRid)

            supplement_num = product_num - len(brand_recommend_product)
            if supplement_num:
                supplement_product = Products.query.filter(
                    Products.isdelete == false(), Products.PBid == brand.PBid).order_by(
                    Products.createtime.desc(), Products.PRid.notin_(pr_supplement_id)).all()
                brand_recommend_product.extend(supplement_product[:supplement_num])
            if brand_recommend_product:
                brand.fill('recommend', brand_recommend_product)

        # 新品推荐
        if new_product:
            brand_new_prodct = Products.query.filter(
                Products.isdelete == false(), Products.PBid == brand.PBid).order_by(Products.createtime.desc()).all()
            brand_new_prodct = brand_new_prodct[:self.br_new]
            if brand_new_prodct:
                for product in brand_new_prodct: product.fields = product_fields
                brand.fill('new', brand_new_prodct)

        # todo 填充动态
        # brand.fill('BrandTweets', list())

        # 填充banner
        if banner_show:
            bb_list = BrandBanner.query.filter(
                BrandBanner.PBid == brand.PBid, BrandBanner.isdelete == false()).order_by(
                BrandBanner.BBsort.asc(), BrandBanner.createtime.desc()).all()
            bbs = self._fill_bb(bb_list)
            if bbs:
                brand.fill('brandbanner', bbs)

    def _recommend_pb_product(self, pbid):
        return Products.query.filter(
            Items.isdelete == false(),
            ProductItems.isdelete == false(),
            Products.isdelete == false(),
            Items.ITid == self.itid_re_pr,
            ProductItems.ITid == Items.ITid,
            Products.PRid == ProductItems.PRid,
            Products.PRstatus == ProductStatus.usual.value,
            Products.PBid == pbid
        ).order_by(ProductItems.createtime.desc())

    def get_recommend_product(self):
        pbid = parameter_required({'pbid': '品牌已下架'})
        ProductBrand.query.filter(ProductBrand.PBid == pbid, ProductBrand.isdelete == false()).first_('品牌已下架')
        pb_list = self._recommend_pb_product(pbid).all_with_page()
        return Success(data=pb_list)

    def _get_brand_coupon(self, suid, user=None, coid_list=[]):
        brand_coupon = Coupon.query.filter(
            Items.isdelete == false(),
            CouponItem.isdelete == false(),
            Coupon.isdelete == false(),
            Items.ITid == self.itid_re_ca,
            CouponItem.ITid == Items.ITid,
            CouponItem.COid == Coupon.COid,
            Coupon.SUid == suid,
            Coupon.COid.notin_(coid_list)
        ).order_by(CouponItem.createtime.desc()).first()
        if not brand_coupon:
            return
        # 过滤已领优惠券
        if user:
            # user = get_current_user()
            couponuser = CouponUser.query.filter(
                CouponUser.USid == user.USid,
                CouponUser.COid == brand_coupon.COid,
                CouponUser.isdelete == false()
            ).first()
            if couponuser:
                coid_list.append(brand_coupon.COid)
                return self._get_brand_coupon(suid, user, coid_list)

        return brand_coupon

    @token_required
    def set_banner(self):
        data = parameter_required({'pbid': '品牌唯一值缺失'})
        pbid = data.get('pbid')
        if is_supplizer():

            supplizer = get_current_supplizer()
            ProductBrand.query.filter(
                ProductBrand.PBid == pbid, ProductBrand.SUid == supplizer.SUid).first_('只能修改自己的品牌')
        elif is_admin():
            ProductBrand.query.filter(
                ProductBrand.PBid == pbid).first_('品牌不存在')
        else:
            raise AuthorityError()
        bbid = data.get('bbid')
        bbcontent = data.get('bbcontent')
        if bbcontent:
            try:
                bbcontent = json.dumps(bbcontent)
            except Exception as e:
                current_app.logger.info('转置json 出错 bbcontent = {} e = {}'.format(bbcontent, e))
        bbsort = data.get('bbsort')
        if bbsort:
            bbsort = self._check_sort(bbsort, model=BrandBanner, filter_args=[BrandBanner.PBid == pbid], default=1)
        with db.auto_commit():
            if bbid:
                if data.get('delete'):
                    BrandBanner.query.filter(BrandBanner.BBid == bbid, BrandBanner.isdelete == false()).delete_(
                        synchronize_session=False)
                    return Success('删除成功')

                bb = BrandBanner.query.filter(BrandBanner.BBid == bbid, BrandBanner.isdelete == false()).first()
                if bb:
                    if bbsort:
                        bb.BBsort = bbsort
                    if bbcontent:
                        bb.BBcontent = bbcontent
                    return Success('更新成功', data=bbid)
            bbid = str(uuid.uuid1())
            if not bbcontent:
                raise ParamsError('轮播图图片路由缺失')
            bb = BrandBanner.create({
                'BBid': bbid,
                'PBid': pbid,
                'BBsort': bbsort or 1,
                'BBcontent': bbcontent
            })
            db.session.add(bb)

        return Success('添加成功', data=bbid)

    def _check_sort(self, sort, model=BrandBanner, filter_args=[], default=None):
        if not sort:
            return default
        try:
            sort = int(sort)
        except:
            current_app.logger.info('转置数字失败 sort = {}'.format(sort))
            return default

        if sort < 1:
            return 1

        bbcount = model.query.filter(model.isdelete == false(), *filter_args).count()
        if sort > bbcount:
            if bbcount >= 1:
                return bbcount
            else:
                return 1
        return sort

    def get_banner(self):
        pbid = parameter_required({'pbid': '品牌唯一值缺失'}).get('pbid')
        bb_list = BrandBanner.query.filter(BrandBanner.PBid == pbid, BrandBanner.isdelete == false()).order_by(
            BrandBanner.BBsort.asc(), BrandBanner.createtime.desc()).all()
        bbs = self._fill_bb(bb_list)
        return Success(data=bbs)

    def _fill_bb(self, bb_list):
        bbs = list()
        for bb in bb_list:
            bbcontent = bb.BBcontent
            try:
                bbcontent = json.loads(bbcontent)
            except:
                current_app.logger.info('转换json 失败 bbid = {}'.format(bb.BBid))
                continue
            bb.fill('bbcontent', bbcontent)
            bbs.append(bb)
        return bbs
