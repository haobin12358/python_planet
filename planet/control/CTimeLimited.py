import json
import math
import uuid
from datetime import datetime, date, timedelta

from flask import request, current_app

from planet.common.params_validates import parameter_required
from planet.common.success_response import Success
from planet.common.token_handler import token_required, get_current_user, is_supplizer, is_admin, admin_required
from planet.config.enums import ApplyStatus, OrderMainStatus, OrderFrom, Client, ActivityType, PayType, ProductStatus, \
    ApplyFrom, TimeLimitedStatus
from planet.common.error_response import StatusError, ParamsError, AuthorityError, DumpliError
from planet.control.BaseControl import BASEAPPROVAL
from planet.control.COrder import COrder
from planet.extensions.register_ext import db
from planet.extensions.validates.activty import ListFreshmanFirstOrderApply, ShelfFreshManfirstOrder
from planet.models import FreshManFirstApply, Products, FreshManFirstProduct, FreshManFirstSku, ProductSku, \
    ProductSkuValue, OrderMain, Activity, UserAddress, AddressArea, AddressCity, AddressProvince, OrderPart, OrderPay, \
    FreshManJoinFlow, ProductMonthSaleValue, ProductImage, ProductBrand, Supplizer, Admin, Approval, ProductCategory, \
    ProductItems, Items, TimeLimitedActivity, TimeLimitedProduct, TimeLimitedSku
from .CUser import CUser


class CTimeLimited(COrder, CUser):

    def list_activity(self):
        """获取活动列表"""
        time_now = datetime.now()
        time_limited_list = TimeLimitedActivity.query.filter(
            TimeLimitedActivity.TLAendTime >= time_now,
            TimeLimitedActivity.isdelete == False,
            TimeLimitedActivity.TLAstatus == TimeLimitedStatus.publish.value
        ).order_by(TimeLimitedActivity.createtime.desc()).all()
        return Success(data=time_limited_list)

    def list_product(self):
        """获取活动商品"""
        data = parameter_required(('tlaid',))
        tlp_list = TimeLimitedProduct.query.filter(
            TimeLimitedProduct.isdelete == False,
            TimeLimitedProduct.TLAid == data.get('tlaid'),
        ).order_by(TimeLimitedProduct.createtime.desc()).all()
        product_list = list()
        for tlp in tlp_list:
            product = self._fill_tlp(tlp)
            if product:
                product_list.append(product)

        # 筛选后重新分页
        page = int(data.get('page_num', 1)) or 1
        count = int(data.get('page_size', 15)) or 15
        total_count = len(product_list)
        if page < 1:
            page = 1
        total_page = math.ceil(total_count / int(count)) or 1
        start = (page - 1) * count
        if start > total_count:
            start = 0
        if total_count / (page * count) < 0:
            ad_return_list = product_list[start:]
        else:
            ad_return_list = product_list[start: (page * count)]
        request.page_all = total_page
        request.mount = total_count
        return Success(data=ad_return_list)

    def get(self):
        """获取单个新人商品"""
        data = parameter_required(('tlpid', ))
        tlp = TimeLimitedProduct.query.filter(TimeLimitedProduct.isdelete == False,
                                              TimeLimitedProduct.TLPid == data.get('tlpid')).first_('活动商品已售空')
        return Success(data=self._fill_tlp(tlp))

    @token_required
    def add_order(self):
        pass

    @admin_required
    def create(self):
        data = parameter_required(('tlastarttime', 'tlaendtime', 'tlatoppic', 'tlaname'))
        tla = TimeLimitedActivity.query.filter(
            TimeLimitedActivity.isdelete == False,
            TimeLimitedActivity.TlAname == data.get('tlaname'),
            TimeLimitedActivity.TLAstatus == TimeLimitedStatus.publish.value
        ).first()
        if tla:
            raise ParamsError('活动名与正在进行的活动重复')
        tla = TimeLimitedActivity.create({
            'TLAid': str(uuid.uuid1()),
            'TLAstartTime': data.get('tlastarttime'),
            'TLAtopPic': data.get('tlatoppic'),
            'TLAendTime': data.get('tlaendtime'),
            'TlAname': data.get('tlaname'),
            'ADid': request.user.id,
        })
        with db.auto_commit():
            db.session.add(tla)

        return Success('创建活动成功', data={'tlaid': tla.TLAid})

    def apply_award(self):
        """申请添加商品"""
        if not (is_supplizer() or is_admin()):
            raise AuthorityError()
        data = parameter_required(('prid', 'prprice', 'skus', 'tlaid'))
        tlp = TimeLimitedProduct.query.filter(
            TimeLimitedProduct.TLAid == data.get('tlaid'), TimeLimitedProduct.PRid == data.get('prid')).first()
        if tlp:
            raise DumpliError('重复提交')
        filter_args = {
            Products.PRid == data.get('prid'),
            Products.isdelete == False,
            Products.PRstatus == ProductStatus.usual.value}
        if is_supplizer():
            tlp_from = ApplyFrom.supplizer.value
            suid = request.user.id
            filter_args.add(Products.PRfrom == tlp_from)
            filter_args.add(Products.CreaterId == suid)
        else:
            tlp_from = ApplyFrom.platform.value
            filter_args.add(Products.PRfrom == tlp_from)
            suid = None
        # tlp_from = ApplyFrom.supplizer.value if is_supplizer() else ApplyFrom.platform.value

        product = Products.query.filter(*filter_args).first_('商品未上架')
        # instance_list = list()
        skus = data.get('skus')
        tla = TimeLimitedActivity.query.filter(TimeLimitedActivity.isdelete == False, TimeLimitedActivity.TLAid == data.get('tlaid')).first_('活动已停止报名')
        tlp = TimeLimitedProduct.create({
            'TLPid': str(uuid.uuid1()),
            'TLAid': tla.TLAid,
            'TLAfrom': tlp_from,
            'SUid': suid,
            'PRid': product.PRid,
            # 'PRmainpic': product.PRmainpic,
            # 'PRattribute': product.PRattribute,
            # 'PBid': product.PBid,
            # 'PBname': product.PBname,
            # 'PRtitle': product.PRtitle,
            'PRprice': data.get('prprice')
        })
        instance_list = [tlp]
        for sku in skus:
            skuid = sku.get('skuid')
            skuprice = sku.get('skuprice')
            skustock = sku.get('skustock')
            sku_instance = ProductSku.query.filter_by(
                isdelete=False, PRid=product.PRid, SKUid=skuid).first_('商品sku信息不存在')
            self._update_stock(-int(skustock), product, sku_instance)
            tls = TimeLimitedSku.create({
                'TLSid': str(uuid.uuid1()),
                'TLPid': tlp.TLPid,
                'TLSstock': skustock,
                'SKUid': skuid,
                'SKUprice': skuprice
            })
            instance_list.append(tls)
            # prstock += skustock
        # todo  添加到审批流
        # with db.auto_commit():
        #     db.session.add_all(instance_list)
        # super(CTimeLimited, self).create_approval('totimelimited', request.user.id, tlp.TLPid)
        return Success('申请成功', {'tlpid': tlp.TLPid})

    def update_award(self):
        """修改"""


    def award_detail(self):
        """查看申请详情"""


    def list_apply(self):
        """查看申请列表"""


    def shelf_award(self):
        """撤销申请"""


    def del_award(self):
        """删除申请"""

    @staticmethod
    def _getBetweenDay(begin_date, end_date):
        date_list = []
        begin_date = datetime.strptime(begin_date, "%Y-%m-%d")
        end_date = datetime.strptime(end_date, "%Y-%m-%d")
        while begin_date <= end_date:
            date_str = begin_date.strftime("%Y-%m-%d")
            date_list.append(date_str)
            begin_date += timedelta(days=1)
        return date_list

    def _re_stock(self, apply):
        """库存回复"""
        apply_skus = FreshManFirstSku.query.join(
            FreshManFirstProduct, FreshManFirstProduct.FMFPid == FreshManFirstSku.FMFPid).filter(
            FreshManFirstProduct.FMFAid == apply.FMFAid).all()
        for apply_sku in apply_skus:
            sku = ProductSku.query.filter(ProductSku.SKUid == apply_sku.SKUid).first()
            product = Products.query.filter(Products.PRid == sku.PRid).first()
            # 加库存
            self._update_stock(apply_sku.FMFPstock, product, sku)

    def _fill_tlp(self, tlp):
        if not tlp:
            return
        product = Products.query.filter(
            Products.PRid == tlp.PRid, Products.isdelete == False).first()
        if not product:
            current_app.logger.info('·商品已删除 prid = {}'.format(tlp.PRid))
        if isinstance(product.PRattribute, str):
            product.PRattribute = json.loads(product.PRattribute)
        if isinstance(getattr(product, 'PRremarks', None) or '{}', str):
            product.PRremarks = json.loads(getattr(product, 'PRremarks', None) or '{}')

        pb = ProductBrand.query.filter_by(PBid=product.PBid, isdelete=False).first()

        images = ProductImage.query.filter(
            ProductImage.PRid == product.PRid, ProductImage.isdelete == False).order_by(
            ProductImage.PIsort).all()
        product.fill('images', images)
        product.fill('brand', pb)
        tls_list = TimeLimitedSku.query.filter_by(TLPid=tlp.TLPid, isdelete=False).all()
        skus = list()
        sku_value_item = list()
        for tls in tls_list:
            sku = ProductSku.query.filter_by(SKUid=tls.SKUid, isdelete=False).first()
            if not sku:
                current_app.logger.info('该sku已删除 skuid = {0}'.format(tls.SKUid))
                continue
            sku.hide('SKUprice')
            sku.hide('SKUstock')
            sku.fill('skuprice', tls.SKUprice)
            sku.fill('skustock', tls.SKUstock)

            if isinstance(sku.SKUattriteDetail, str):
                sku.SKUattriteDetail = json.loads(sku.SKUattriteDetail)
            sku_value_item.append(sku.SKUattriteDetail)
            skus.append(sku)
        if not skus:
            current_app.logger.info('该申请的商品没有sku prid = {0}'.format(product.PRid))
            return
        product.fill('skus', skus)
        sku_value_item_reverse = []
        for index, name in enumerate(product.PRattribute):
            value = list(set([attribute[index] for attribute in sku_value_item]))
            value = sorted(value)
            temp = {
                'name': name,
                'value': value
            }
            sku_value_item_reverse.append(temp)
        product.fill('SkuValue', sku_value_item_reverse)
        return product


