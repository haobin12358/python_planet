# -*- coding: utf-8 -*-
import uuid

from planet.common.params_validates import parameter_required
from planet.config.enums import ProductBrandStatus, ProductStatus, ItemType
from planet.service.SProduct import SProducts
from planet.models import ProductBrand, IndexBrand, Products, Items, BrandWithItems
from planet.common.success_response import Success
from planet.common.token_handler import token_required
from planet.extensions.validates.product import BrandsListForm, BrandsCreateForm, BrandUpdateForm


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
            if itids:
                for itid in itids:
                    s.query(Items).filter_by_({'ITid': itid, 'ITtype': ItemType.brand.value}).first_('{}标签不存在或类型不正确'.format(itid))
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
        index = dict(form.index.choices).get(form.index.data)
        time_order = dict(form.time_order.choices).get(form.time_order.data)
        pbstatus = dict(form.pbstatus.choices).get(form.pbstatus.data)
        itid = form.itid.data
        with self.sproduct.auto_commit() as s:
            brands = s.query(ProductBrand).filter_by_().outerjoin(BrandWithItems, BrandWithItems.PBid == ProductBrand.PBid)
            if index:  # 在首页的
                brands = brands.join(
                    IndexBrand, IndexBrand.PBid == ProductBrand.PBid
                ).filter_(
                    IndexBrand.isdelete == False,
                    BrandWithItems.ITid == itid,
                    ProductBrand.PBstatus == pbstatus).order_by(*[time_order]).all_with_page()
            elif index is False:  # 不在首页的
                index_brands = s.query(IndexBrand).filter_by_().all()
                brands = brands.filter_(ProductBrand.PBid.notin_([x.PBid for x in index_brands]),
                                                       ProductBrand.PBstatus == pbstatus, BrandWithItems.ITid == itid).\
                    order_by(*[time_order]).all_with_page()
            elif index is None:  # 不筛选首页
                brands = brands.filter_(ProductBrand.PBstatus == pbstatus, BrandWithItems.ITid == itid).order_by(*[time_order]).all_with_page()
            for brand in brands:
                is_index = s.query(IndexBrand).filter_by_({'PBid': brand.PBid}).first_()
                brand.fill('PBstatus_en', ProductBrandStatus(brand.PBstatus).name)
                brand.fill('index', bool(is_index))
                # 标签
                pb_items = s.query(Items).filter_by().join(BrandWithItems, Items.ITid == BrandWithItems.ITid).filter_(
                    BrandWithItems.PBid == brand.PBid,
                    BrandWithItems.isdelete == False,
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
        itids = form.itids.data
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
            if old_item_id:
                s.query(BrandWithItems).filter_(BrandWithItems.ITid.in_(old_item_id)).delete_(synchronize_session=False)
        return Success('更新成功')


