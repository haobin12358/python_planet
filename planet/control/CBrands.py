# -*- coding: utf-8 -*-
import uuid

from planet.common.params_validates import parameter_required
from planet.config.enums import ProductBrandStatus, ProductStatus
from planet.service.SProduct import SProducts
from planet.models import ProductBrand, IndexProductBrand, Products, BrandWithItems, BrandItems
from planet.common.success_response import Success
from planet.common.token_handler import token_required
from planet.validates.product import BrandsListForm, BrandsCreateForm, BrandUpdateForm


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
        biids = data.biids.data
        with self.sproduct.auto_commit() as s:
            s_list = []

            pbid = str(uuid.uuid4())
            pb_dict = {
                'PBid': pbid,
                'PBlogo': pblogo,
                'PBname': pbname,
                'PBdesc': pbdesc,
                'PBlinks': pblinks,
            }
            pb_instance = ProductBrand.create(pb_dict)
            s_list.append(pb_instance)
            # 创建标签-品牌中间表
            if biids:
                for biid in biids:
                    s.query(BrandItems).filter_by_({'BIid': biid}).first_('标签不存在{}'.format(biid))
                    brand_with_pbitem_instance = BrandWithItems.create({
                        'BWIid': str(uuid.uuid4()),
                        'BIid': biid,
                        'PBid': pbid
                    })
                    s_list.append(brand_with_pbitem_instance)
            s.add_all(s_list)
        return Success('添加成功', {'pbid': pb_instance.PBid})

    def list(self):
        form = BrandsListForm().valid_data()
        index = dict(form.index.choices).get(form.index.data)
        time_order = dict(form.time_order.choices).get(form.time_order.data)
        pbstatus = dict(form.pbstatus.choices).get(form.pbstatus.data)
        biid = form.biid.data
        with self.sproduct.auto_commit() as s:
            brands = s.query(ProductBrand).filter_by_().outerjoin(BrandWithItems, BrandWithItems.PBid == ProductBrand.PBid)
            if index:  # 在首页的
                brands = brands.join(
                    IndexProductBrand, IndexProductBrand.PBid == ProductBrand.PBid
                ).filter_(
                    IndexProductBrand.isdelete == False,
                    BrandWithItems.BIid == biid,
                    ProductBrand.PBstatus == pbstatus).order_by(*[time_order]).all_with_page()
                for brand in brands:
                    brand.fill('PBstatus_en', ProductBrandStatus(brand.PBstatus).name)
                    brand.fill('index', True)
                    # 标签
                    pb_items = s.query(BrandItems).join(BrandWithItems, BrandItems.BIid == BrandWithItems.BIid).filter_(
                        BrandWithItems.PBid == brand.PBid
                    ).all()
                    brand.fill('pb_items', pb_items)
            elif index is False:  # 不在首页的
                index_brands = s.query(IndexProductBrand).filter_by_().all()
                brands = brands.filter_(ProductBrand.PBid.notin_([x.PBid for x in index_brands]),
                                                       ProductBrand.PBstatus == pbstatus, BrandWithItems.BIid == biid).\
                    order_by(*[time_order]).all_with_page()
                for brand in brands:
                    brand.fill('PBstatus_en', ProductBrandStatus(brand.PBstatus).name)
                    brand.fill('index', False)
                    # 标签
                    pb_items = s.query(BrandItems).join(BrandWithItems, BrandItems.BIid == BrandWithItems.BIid).filter_(
                        BrandWithItems.PBid == brand.PBid
                    ).all()
                    brand.fill('pb_items', pb_items)
            elif index is None:  # 不筛选首页
                brands = brands.filter_(ProductBrand.PBstatus == pbstatus, BrandWithItems.BIid == biid).order_by(*[time_order]).all_with_page()
                for brand in brands:
                    is_index = s.query(IndexProductBrand).filter_by_({'PBid': brand.PBid}).first_()
                    brand.fill('PBstatus_en', ProductBrandStatus(brand.PBstatus).name)
                    brand.fill('index', bool(is_index))
                    # 标签
                    pb_items = s.query(BrandItems).join(BrandWithItems, BrandItems.BIid == BrandWithItems.BIid).filter_(
                        BrandWithItems.PBid == brand.PBid
                    ).all()
                    brand.fill('pb_items', pb_items)
        return Success(data=brands)

    @token_required
    def off_shelves(self):
        """下架"""
        data = parameter_required(('pbid',))
        pbid = data.get('pbid')
        with self.sproduct.auto_commit() as s:
            s_list = []
            # 下架品牌
            product_brand_instance = s.query(ProductBrand).filter_by_({
                'PBid': pbid
            }).first_('品牌不存在')
            product_brand_instance.PBstatus = ProductBrandStatus.off_shelves.value
            s_list.append(product_brand_instance)
            # 下架商品
            s.query(Products).filter_by_({'PBid': pbid}).update({
                'PRstatus': ProductStatus.off_shelves.value
            })
            s.add_all(s_list)
        return Success('下架成功')

    @token_required
    def update(self):
        form = BrandUpdateForm().valid_data()
        pbid = form.pbid.data
        biids = form.biids.data
        with self.sproduct.auto_commit() as s:
            s_list = []
            product_brand_instance = s.query(ProductBrand).filter_by_({
                'PBid': pbid
            }).first_('不存在的品牌')
            product_brand_instance.update({
                'PBlogo': form.pblogo.data,
                'PBname': form.pbname.data,
                'pbdesc': form.pbdesc.data,
                'pblinks': form.pblinks.data,
            })
            s_list.append(product_brand_instance)
            if biids:
                # 已存在的标签
                brand_with_item = ''
                for biid in biids:


                    s.query(BrandItems).filter_by_({'BIid': biid}).first_('标签不存在{}'.format(biid))

                    brand_with_pbitem_instance = BrandWithItems.create({
                        'BWIid': str(uuid.uuid4()),
                        'BIid': biid,
                        'PBid': pbid
                    })
                    s_list.append(brand_with_pbitem_instance)
        return Success('更新成功')






