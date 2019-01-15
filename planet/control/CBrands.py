# -*- coding: utf-8 -*-
import uuid

from flask import current_app
from sqlalchemy import or_

from planet.common.params_validates import parameter_required
from planet.config.enums import ProductBrandStatus, ProductStatus, ItemType
from planet.extensions.register_ext import db
from planet.service.SProduct import SProducts
from planet.models import ProductBrand, Products, Items, BrandWithItems, Supplizer
from planet.common.success_response import Success
from planet.common.token_handler import token_required, is_supplizer, is_admin, admin_required
from planet.extensions.validates.product import BrandsListForm, BrandsCreateForm, BrandUpdateForm, request


class CBrands(object):
    def __init__(self):
        self.sproduct = SProducts()

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
        with self.sproduct.auto_commit() as s:
            s_list = []
            pbid = str(uuid.uuid1())
            pb_dict = {
                'PBid': pbid,
                'PBlogo': pblogo,
                'PBname': pbname,
                'PBdesc': pbdesc,
                'PBlinks': pblinks,
                'PBbackgroud': pbbackgroud,
                'SUid': suid
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
        time_order = dict(form.time_order.choices).get(form.time_order.data)
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
        brands = brand_query.order_by(time_order).all_with_page()
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
        return Success(data=brands)

    def get(self):
        data = parameter_required(('pbid',))
        pbid = data.get('pbid')
        product_brand = ProductBrand.query.filter_by({'PBid': pbid}).first_('品牌不存在')
        product_brand.fill('pbstatus_en', ProductStatus(product_brand.PBstatus).name)
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
        data = parameter_required(('pbid', ))
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

        with self.sproduct.auto_commit() as s:
            s_list = []
            product_brand_instance = s.query(ProductBrand).filter_by_({
                'PBid': pbid
            }).first_('不存在的品牌')
            product_brand_instance.update({
                'PBlogo': pblogo,
                'PBname': pbname,
                'PBdesc': pbdesc,
                'PBlinks': pblinks,
                'PBbackgroud': pbbackgroud,
                'SUid': suid
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
        data = parameter_required(('pbid', ))
        pbid = data.get('pbid')
        with db.auto_commit():
            brand = ProductBrand.query.filter(
                ProductBrand.PBid == pbid,
                ProductBrand.isdelete == False
            ).first_('品牌不存在')
            brand.isdelete = True
            db.session.add(brand)
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
