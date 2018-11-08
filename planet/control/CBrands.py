# -*- coding: utf-8 -*-
import uuid

from sqlalchemy.testing import in_, not_in_

from planet.common.params_validates import parameter_required
from planet.config.enums import ProductBrandStatus, ProductStatus
from planet.service.SProduct import SProducts
from planet.models import ProductBrand, IndexProductBrand, Products
from planet.common.success_response import Success
from planet.common.token_handler import token_required, is_admin
from planet.validates.brands import BrandsListForm, BrandsCreateForm


class CBrands(object):
    def __init__(self):
        self.sproduct = SProducts()

    @token_required
    def create(self):
        """创建品牌"""
        data = BrandsCreateForm().validate_for_api()
        pblogo = data.pblogo.data
        pbname = data.pbname.data
        pbdesc = data.pbdesc.data
        pblinks = data.pblinks.data
        with self.sproduct.auto_commit() as s:
            pb_dict = {
                'PBid': str(uuid.uuid4()),
                'PBlogo': pblogo,
                'PBname': pbname,
                'PBdesc': pbdesc,
                'PBlinks': pblinks,
            }
            pb_instance = ProductBrand.create(pb_dict)
            s.add(pb_instance)
        return Success('添加成功', {'pbid': pb_instance.PBid})

    def list(self):
        form = BrandsListForm().validate_for_api()
        index = dict(form.index.choices).get(form.index.data)
        time_order = dict(form.time_order.choices).get(form.time_order.data)
        pbstatus = dict(form.pbstatus.choices).get(form.pbstatus.data)
        with self.sproduct.auto_commit() as s:
            if index:  # 在首页的
                brands = s.query(ProductBrand).join(
                    IndexProductBrand, IndexProductBrand.PBid == ProductBrand.PBid
                ).filter_(IndexProductBrand.isdelete == False, ProductBrand.PBstatus == pbstatus).order_by(*[time_order]).all_with_page()
                for brand in brands:
                    brand.fill('PBstatus_en', ProductBrandStatus(brand.PBstatus).name)
                    brand.fill('index', True)
            elif index is False:  # 不在首页的
                index_brands = s.query(IndexProductBrand).filter_by_().all()
                brands = s.query(ProductBrand).filter_(ProductBrand.PBid.notin_([x.PBid for x in index_brands]),
                                                       ProductBrand.PBstatus == pbstatus).\
                    order_by(*[time_order]).all_with_page()
                for brand in brands:
                    brand.fill('PBstatus_en', ProductBrandStatus(brand.PBstatus).name)
                    brand.fill('index', False)
            elif index is None:
                brands = s.query(ProductBrand).filter_by_({'PBstatus': pbstatus}).order_by(*[time_order]).all_with_page()
                for brand in brands:
                    is_index = s.query(IndexProductBrand).filter_by_({'PBid': brand.PBid}).first_()
                    brand.fill('PBstatus_en', ProductBrandStatus(brand.PBstatus).name)
                    brand.fill('index', bool(is_index))
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

