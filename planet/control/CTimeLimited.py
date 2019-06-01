import json
import math
import uuid
import copy
from datetime import datetime, timedelta
from flask import request, current_app
from planet.common.params_validates import parameter_required
from planet.common.success_response import Success
from planet.common.token_handler import token_required, is_supplizer, is_admin, admin_required, common_user
from planet.config.enums import ApplyStatus, ProductStatus, ApplyFrom, TimeLimitedStatus, AdminAction, AdminActionS
from planet.common.error_response import StatusError, ParamsError, AuthorityError, DumpliError
from planet.control.BaseControl import BaseController
from planet.control.COrder import COrder
from planet.control.BaseControl import BASEADMIN
from planet.extensions.register_ext import db, conn
from planet.extensions.tasks import end_timelimited, start_timelimited, celery
from planet.models import Products, ProductSku, ProductImage, ProductBrand, Supplizer, Admin, Approval, \
    TimeLimitedActivity, TimeLimitedProduct, TimeLimitedSku, IndexBanner, Commision, AdminActions
from .CUser import CUser


class CTimeLimited(COrder, CUser, BaseController):

    def list_activity_product(self):
        """获取活动列表"""
        # 根据分类查询
        time_now = datetime.now()
        filter_args = {
            TimeLimitedActivity.isdelete == False,
            TimeLimitedActivity.TLAstatus.in_([
                TimeLimitedStatus.waiting.value, TimeLimitedStatus.starting.value])
        }

        time_limited_list = TimeLimitedActivity.query.filter(*filter_args).order_by(
            TimeLimitedActivity.TLAstartTime.asc()).all()

        for time_limited in time_limited_list:
            time_limited.fill('tlastatus_zh', TimeLimitedStatus(time_limited.TLAstatus).zh_value)
            time_limited.fill('tlastatus_en', TimeLimitedStatus(time_limited.TLAstatus).name)
            tlp_query = TimeLimitedProduct.query.join(Products, Products.PRid == TimeLimitedProduct.PRid).filter(
                TimeLimitedProduct.TLAid == time_limited.TLAid,
                TimeLimitedProduct.isdelete == False,
                Products.isdelete == False,
                Products.PRstatus == ProductStatus.usual.value,
                TimeLimitedProduct.TLAstatus.in_([ApplyStatus.agree.value,ApplyStatus.lose_agree.value])
            )
            tlp_count = tlp_query.count()
            time_limited.fill('prcount', tlp_count)
            if time_limited.TLAstatus == TimeLimitedStatus.waiting.value:
                if isinstance(time_limited.TLAstartTime, datetime):
                    starttime = time_limited.TLAstartTime
                else:
                    starttime = datetime.strptime(str(time_limited.TLAstartTime), '%Y-%m-%d %H:%M:%S')
                time_limited.fill('duration_start', str(starttime - time_now))
            if time_limited.TLAstatus == TimeLimitedStatus.starting.value:
                if isinstance(time_limited.TLAendTime, datetime):
                    end_time = time_limited.TLAendTime
                else:
                    end_time = datetime.strptime(str(time_limited.TLAendTime), '%Y-%m-%d %H:%M:%S')
                time_limited.fill('duration_end', str(end_time - time_now))

            tlp_list = tlp_query.order_by(TimeLimitedProduct.createtime.desc()).all()

            product_list = list()
            for tlp in tlp_list:
                product = self._fill_tlp(tlp, time_limited)
                if product:
                    product_list.append(product)
            ad_return_list = product_list[:8]
            time_limited.fill('product_list', ad_return_list)

        return Success(data=time_limited_list)

    def list_activity(self):
        """获取活动列表"""
        # 根据分类查询
        time_now = datetime.now()
        data = parameter_required()
        tlastatus = data.get('tlastatus')
        tlaname = data.get('tlaname', '')
        tlastarttime = data.get('tlastarttime')
        tlaendtime = data.get('tlaendtime')

        filter_args = {
            TimeLimitedActivity.isdelete == False,
        }
        order_by_args = []
        if not (is_admin() or is_supplizer()):
            filter_args.add(TimeLimitedActivity.TLAendTime >= time_now)
            filter_args.add(TimeLimitedActivity.TLAstatus.in_([
                TimeLimitedStatus.waiting.value, TimeLimitedStatus.starting.value]))
            order_by_args.append(TimeLimitedActivity.TLAstartTime.asc())
        else:
            current_app.logger.info('本次是管理员进行查询')
            if tlastatus or tlastatus == 0:
                filter_args.add(TimeLimitedActivity.TLAstatus == tlastatus)
            order_by_args.extend([TimeLimitedActivity.TLAsort.asc(), TimeLimitedActivity.createtime.asc()])
        if tlaname:
            filter_args.add(TimeLimitedActivity.TlAname.ilike('%{}%'.format(tlaname)))
        if tlastarttime:
            filter_args.add(TimeLimitedActivity.TLAstartTime >= tlastarttime)
        if tlaendtime:
            filter_args.add(TimeLimitedActivity.TLAendTime <= tlaendtime)

        time_limited_list = TimeLimitedActivity.query.filter(*filter_args).order_by(*order_by_args).all()
        for time_limited in time_limited_list:
            self._fill_tla(time_limited, time_now)
        return Success(data=time_limited_list)

    def list_product(self):
        """获取活动商品"""
        data = parameter_required(('tlaid',))
        tlaid = data.get('tlaid')
        tlastatus = data.get('tlastatus')
        prtitle = data.get('prtitle', '')
        filter_args = {
            TimeLimitedProduct.isdelete == False,
        }
        if common_user():
            filter_args.add(TimeLimitedProduct.TLAstatus.in_([ApplyStatus.agree.value, ApplyStatus.lose_agree.value]))
            current_app.logger.info('本次是普通用户进行查询')
        elif is_supplizer():
            current_app.logger.info('本次是供应商进行查询')
            filter_args.add(TimeLimitedProduct.SUid == request.user.id)

        else:
            current_app.logger.info('本次是管理员进行查询')

        if tlaid:
            filter_args.add(TimeLimitedProduct.TLAid == data.get('tlaid'))
        if tlastatus:
            filter_args.add(TimeLimitedProduct.TLAstatus == data.get('tlastatus'))
        if prtitle:
            filter_args.add(Products.PRtitle.ilike('%{}%'.format(prtitle)))

        # filter_args.add(TimeLimitedProduct.TLAstatus >= ApplyStatus.shelves.value)
        tlp_list = TimeLimitedProduct.query.join(Products, Products.PRid == TimeLimitedProduct.PRid).filter(
            *filter_args).order_by(
            TimeLimitedProduct.createtime.desc()).all()
        product_list = list()
        # tlaid = tlp.TLAid
        if common_user():
            tla = TimeLimitedActivity.query.filter(
                TimeLimitedActivity.isdelete == False,
                TimeLimitedActivity.TLAid == tlaid,
                TimeLimitedActivity.TLAstatus.in_(
                    [TimeLimitedStatus.waiting.value, TimeLimitedStatus.starting.value])
            ).first_('活动已下架')
        else:
            tla = TimeLimitedActivity.query.filter(
                TimeLimitedActivity.isdelete == False,
                TimeLimitedActivity.TLAid == tlaid,
            ).first_('没有此活动')

        for tlps in tlp_list:
            # current_app.logger.info(tlp.TLPid)
            product = copy.deepcopy(self._fill_tlp(tlps, tla))
            # current_app.logger.info(product.tlpid)
            if product:
                # current_app.logger.info(product.tlpid)
                product_list.append(product)
                # current_app.logger.info(product.tlpid)
        for products in product_list:
            current_app.logger.info(products.tlpid)

        # 筛选后重新分页
        page = int(data.get('page_num', 1)) or 1
        count = int(data.get('page_size', 15)) or 15
        total_count = len(product_list)
        current_app.logger.info(page,count,total_count)
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
        # tlakwargs = dict(tlaname=tla.TlAname)
        self._fill_tla(tla)
        # current_app.logger.info(ad_return_list)
        return Success(data=ad_return_list).get_body(tla=tla)

    def get(self):
        """获取单个新人商品"""
        data = parameter_required(('tlpid',))
        tlp = TimeLimitedProduct.query.filter(TimeLimitedProduct.isdelete == False,
                                              TimeLimitedProduct.TLPid == data.get('tlpid')).first_('活动商品已售空')
        tla = TimeLimitedActivity.query.filter(TimeLimitedActivity.isdelete == False,
                                               TimeLimitedActivity.TLAstatus.in_(
                                                   [TimeLimitedStatus.waiting.value, TimeLimitedStatus.starting.value]),
                                               TimeLimitedActivity.TLAid == tlp.TLAid).first_('活动已结束')
        return Success(data=self._fill_tlp(tlp, tla))

    @token_required
    def add_order(self):
        # 该接口废弃
        return

    @admin_required
    def create(self):
        data = parameter_required(('tlastarttime', 'tlaendtime', 'tlatoppic', 'tlaname'))
        tla = TimeLimitedActivity.query.filter(
            TimeLimitedActivity.isdelete == False,
            TimeLimitedActivity.TlAname == data.get('tlaname'),
            TimeLimitedActivity.TLAstatus.in_(
                [TimeLimitedStatus.waiting.value, TimeLimitedStatus.starting.value])
        ).first()
        if tla:
            raise ParamsError('活动名与正在进行的活动重复')
        time_now = datetime.now()
        start_time = datetime.strptime(data.get('tlastarttime'), '%Y-%m-%d %H:%M:%S')
        end_time = datetime.strptime(data.get('tlaendtime'), '%Y-%m-%d %H:%M:%S')
        if start_time > time_now:
            tlastatus = TimeLimitedStatus.waiting.value
        elif end_time < time_now:
            tlastatus = TimeLimitedStatus.end.value
        else:
            tlastatus = TimeLimitedStatus.starting.value

        tla = TimeLimitedActivity.create({
            'TLAid': str(uuid.uuid1()),
            'TLAsort': 1,
            'TLAstartTime': data.get('tlastarttime'),
            'TLAtopPic': data.get('tlatoppic'),
            'TLAendTime': data.get('tlaendtime'),
            'TlAname': data.get('tlaname'),
            'ADid': request.user.id,
            'TLAstatus': tlastatus,
        })
        if tlastatus >= TimeLimitedStatus.waiting.value and tlastatus < TimeLimitedStatus.end.value:
            from planet.config.http_config import API_HOST
            tlb = IndexBanner.create({
                'IBid': str(uuid.uuid1()),
                'IBpic': data.get('tlatoppic'),
                'IBsort': 1,
                'IBshow': False,
                'contentlink': API_HOST + "/?tlaid=" + tla.TLAid + "&secret_usid="
            })
            with db.auto_commit():
                db.session.add(tlb)
                BASEADMIN().create_action(AdminActionS.insert.value, 'TimeLimitedActivity', tla.TLAid)

            current_app.logger.info('增加轮播图成功')
        else:
            current_app.logger.info('没有增加轮播图')
        self._crete_celery_task(tlastatus=tlastatus, tlaid=tla.TLAid, start_time=start_time, end_time=end_time)

        with db.auto_commit():
            db.session.add(tla)
        return Success('创建活动成功', data={'tlaid': tla.TLAid})

    def apply_award(self):
        """申请添加商品"""
        if not (is_supplizer() or is_admin()):
            raise AuthorityError()
        data = parameter_required(('prid', 'prprice', 'skus', 'tlaid'))
        tlp = TimeLimitedProduct.query.filter(
            # TimeLimitedProduct.TLAstatus != ApplyStatus.agree.value,
            TimeLimitedProduct.isdelete == False,
            TimeLimitedProduct.TLAid == data.get('tlaid'),
            TimeLimitedProduct.PRid == data.get('prid')).first()
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
        with db.auto_commit():
            product = Products.query.filter(*filter_args).first_('只能选择自己的商品')
            # instance_list = list()
            skus = data.get('skus')
            tla = TimeLimitedActivity.query.filter(
                TimeLimitedActivity.isdelete == False,
                TimeLimitedActivity.TLAstatus == TimeLimitedStatus.waiting.value,
                TimeLimitedActivity.TLAid == data.get('tlaid')).first_('活动已停止报名')
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
            db.session.add_all(instance_list)
            if is_admin():
                BASEADMIN().create_action(AdminActionS.insert.value, 'TimeLimitedProduct', tlp.TLPid)

        # todo  添加到审批流
        super(CTimeLimited, self).create_approval('totimelimited', request.user.id, tlp.TLPid, applyfrom=tlp_from)

        return Success('申请成功', {'tlpid': tlp.TLPid})

    def reapply_award(self,apply_info,tlp_from,suid,product):
        """重新申请"""
        data = parameter_required(('tlaid', 'tlpid', 'prid', 'prprice', 'skus'))
        with db.auto_commit():
            # 获取申请单
            apply_info.update({"TLAstatus": ApplyStatus.lose_agree.value})
            db.session.add(apply_info)
            skus = data.get('skus')
            tla = TimeLimitedActivity.query.filter(
                TimeLimitedActivity.isdelete == False,
                TimeLimitedActivity.TLAstatus == TimeLimitedStatus.waiting.value,
                TimeLimitedActivity.TLAid == data.get('tlaid')).first_('活动已停止报名')
            new_tlp = TimeLimitedProduct.create({
                'TLPid': str(uuid.uuid1()),
                'TLAid': tla.TLAid,
                'TLAfrom': tlp_from,
                'TLAstatus': ApplyStatus.wait_check.value,
                'SUid': suid,
                'PRid': product.PRid,
                'PRprice': data.get('prprice'),
                'ParentTLPid': apply_info.TLPid
            })
            db.session.add(new_tlp)
            for sku in skus:
                skuid = sku.get('skuid')
                skuprice = sku.get('skuprice')
                skustock = sku.get('skustock')
                sku_instance = ProductSku.query.filter_by(
                    isdelete=False, PRid=product.PRid, SKUid=skuid).first_('商品sku信息不存在')
                self._update_stock(-int(skustock), product, sku_instance)
                tls = TimeLimitedSku.create({
                    'TLSid': str(uuid.uuid1()),
                    'TLPid': new_tlp.TLPid,
                    'TLSstock': skustock,
                    'SKUid': skuid,
                    'SKUprice': skuprice
                })

                db.session.add(tls)
                # prstock += skustock
            if is_admin():
                BASEADMIN().create_action(AdminActionS.insert.value, 'TimeLimitedProduct', new_tlp.TLPid)

        # todo  添加到审批流
        super(CTimeLimited, self).create_approval('totimelimited', request.user.id, new_tlp.TLPid, applyfrom=tlp_from)

        return new_tlp.TLPid

    def update_award(self):
        """修改"""
        data = parameter_required(('tlaid', 'tlpid', 'prid', 'prprice', 'skus'))
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
        apply_info = TimeLimitedProduct.query.filter(
            TimeLimitedProduct.TLPid == data.get('tlpid'),
            TimeLimitedProduct.PRid == data.get('prid'),
            TimeLimitedProduct.isdelete == False
        ).first_('商品不存在')
        if apply_info.TLAstatus not in [ApplyStatus.reject.value, ApplyStatus.cancle.value,
                                        ApplyStatus.agree.value]:
            raise StatusError('此申请不可以进行修改')
        if apply_info.SUid != suid:
            raise AuthorityError('仅可修改自己提交的申请')
        skus = data.get('skus')
        tla = TimeLimitedActivity.query.filter(
            TimeLimitedActivity.isdelete == False,
            TimeLimitedActivity.TLAstatus == TimeLimitedStatus.waiting.value,
            TimeLimitedActivity.TLAid == data.get('tlaid')).first_('活动已停止报名')
        if tla.TLAstatus == TimeLimitedStatus.starting.value:
            raise StatusError('此申请不可以进行修改')
        product = Products.query.filter(*filter_args).first_('商品未上架')
        # 修改父商品状态
        parent_apply = apply_info
        while parent_apply.ParentTLPid:
            current_apply = TimeLimitedProduct.query.filter(TimeLimitedProduct.TLPid == parent_apply.ParentTLPid,
                                                            TimeLimitedProduct.TLAstatus.in_([ApplyStatus.agree.value,ApplyStatus.lose_effect.value]),
                                                            TimeLimitedProduct.isdelete == False).first()
            if current_apply:
                current_app.logger.info('current_apply{}'.format(current_apply.TLPid))
                if current_apply.TLAstatus == ApplyStatus.lose_effect.value:
                    children_apply = TimeLimitedProduct.query.filter(TimeLimitedProduct.ParentTLPid == current_apply.TLPid,
                                                                     TimeLimitedProduct.TLAstatus == ApplyStatus.agree.value,
                                                                     TimeLimitedProduct.isdelete == False).first()
                    if children_apply:
                        current_app.logger.info('child{}'.format(children_apply.TLPid))
                        children_apply.update({"TLAstatus": ApplyStatus.lose_agree.value})
                        db.session.add(children_apply)
                        break
                else:
                    current_apply.update({"TLAstatus": ApplyStatus.lose_agree.value})
                    db.session.add(current_apply)
                    break
            parent_apply = TimeLimitedProduct.query.filter(
                TimeLimitedProduct.TLPid == parent_apply.ParentTLPid).first()
        if apply_info.TLAstatus == ApplyStatus.reject.value or apply_info.TLAstatus == ApplyStatus.cancle.value:
            with db.auto_commit():
                # instance_list = list()
                apply_info.update({
                    'TLAid': tla.TLAid,
                    'TLAfrom': tlp_from,
                    'SUid': suid,
                    'PRid': product.PRid,
                    'PRprice': data.get('prprice'),
                    'TLAstatus': ApplyStatus.wait_check.value
                })
                instance_list = [apply_info]
                skuids = list()
                new_skuid = list()
                # todo  撤销或者拒绝时 退还库存
                for sku in skus:
                    skuid = sku.get('skuid')
                    skuprice = sku.get('skuprice')
                    skustock = sku.get('skustock')
                    sku_instance = ProductSku.query.filter_by(
                        isdelete=False, PRid=product.PRid, SKUid=skuid).first_('商品sku信息不存在')
                    self._update_stock(-int(skustock), product, sku_instance)
                    tls = TimeLimitedSku.query.filter(
                        TimeLimitedSku.TLPid == apply_info.TLPid,
                        TimeLimitedSku.SKUid == skuid,
                        TimeLimitedSku.isdelete == False,
                    ).first()
                    if not tls:
                        tls = TimeLimitedSku.create({
                            'TLSid': str(uuid.uuid1()),
                            'TLPid': apply_info.TLPid,
                            'TLSstock': skustock,
                            'SKUid': skuid,
                            'SKUprice': skuprice
                        })
                        new_skuid.append(tls.TLSid)
                    else:

                        tls.update({
                            'TLPid': apply_info.TLPid,
                            'TLSstock': skustock,
                            'SKUid': skuid,
                            'SKUprice': skuprice
                        })
                    skuids.append(skuid)

                    instance_list.append(tls)
                delete_sku = TimeLimitedSku.query.filter(
                    TimeLimitedSku.isdelete == False,
                    TimeLimitedSku.SKUid.notin_(skuids),
                    TimeLimitedSku.TLPid == apply_info.TLPid
                ).all()
                for tls in delete_sku:
                    sku_instance = ProductSku.query.filter_by(
                        isdelete=False, PRid=product.PRid, SKUid=skuid).first_('商品sku信息不存在')
                    self._update_stock(int(tls.TLSstock), product, sku_instance)
                    tls.isdelete = True

                current_app.logger.info('本次修改 sku {} 个 新增 {} 删除 {} '.format(
                    len(skuids), len(new_skuid), len(delete_sku)))
                # prstock += skustock

                db.session.add_all(instance_list)
                if is_admin():
                    BASEADMIN().create_action(AdminActionS.update.value, 'TimeLimitedProduct', data.get('tlpid'))

            super(CTimeLimited, self).create_approval('totimelimited', request.user.id, apply_info.TLPid,
                                                      applyfrom=tlp_from)
            return Success('修改成功')
        else:
            tlpid = self.reapply_award(apply_info,tlp_from,suid,product)
            return Success('修改成功',{'tlpid': tlpid})

    @admin_required
    def update_activity(self):
        data = parameter_required(('tlaid',))
        with db.auto_commit():
            tla = TimeLimitedActivity.query.filter(
                TimeLimitedActivity.TLAid == data.get('tlaid'),
                TimeLimitedActivity.isdelete == False).first_('活动已删除')
            if data.get('delete'):
                tla.isdelete = True
                tlp_list = TimeLimitedProduct.query.filter(TimeLimitedProduct.isdelete == False,
                                                           TimeLimitedProduct.TLAid == tla.TLAid).all()
                # 如果删除活动的话，退还库存
                for tlp in tlp_list:
                    self._re_stock(tlp)

                BASEADMIN().create_action(AdminActionS.delete.value, 'TimeLimitedActivity', tla.TLAid)
                return Success('删除成功')

            if tla.TLAstatus == TimeLimitedStatus.end.value:
                raise ParamsError('已结束活动禁止重新编辑')

            if tla.TLAstatus == TimeLimitedStatus.starting.value:
                data = dict(tlastatus=data.get('tlastatus'), tlasort=data.get('tlasort'))

            for k in tla.keys():
                if k == 'TLAid' or k == 'isdelete':
                    continue
                low_k = str(k).lower()
                value = data.get(low_k)
                if value or value == 0:
                    if k == 'TLAstatus':
                        try:
                            TimeLimitedStatus(value)
                        except:
                            continue
                    if k == 'TLAsort':
                        value = self._check_sort(value)
                    tla.__setattr__(k, value)

            # if tla.TLAstatus != TimeLimitedStatus.end.value:
            if data.get('tlastatus') != TimeLimitedStatus.abort.value:
                time_now = datetime.now()
                start_time = datetime.strptime(str(tla.TLAstartTime), '%Y-%m-%d %H:%M:%S')
                end_time = datetime.strptime(str(tla.TLAendTime), '%Y-%m-%d %H:%M:%S')
                if time_now < start_time:
                    tlastatus = TimeLimitedStatus.waiting.value
                elif time_now > end_time:
                    tlastatus = TimeLimitedStatus.end.value
                else:
                    tlastatus = TimeLimitedStatus.starting.value

                tla.TLAstatus = tlastatus
                self._crete_celery_task(tlastatus=tlastatus, tlaid=tla.TLAid,
                                        start_time=start_time, end_time=end_time)
                BASEADMIN().create_action(AdminActionS.update.value, 'TimeLimitedActivity', tla.TLAid)
        return Success('修改成功')

    def award_detail(self):
        """查看申请详情"""

    def list_apply(self):
        """查看申请列表"""

    def shelf_award(self):
        """撤销申请"""
        if not (is_supplizer() or is_admin()):
            raise AuthorityError()
        data = parameter_required(('tlpid',))
        tlpid = data.get('tlpid')
        if is_supplizer():
            tlp_from = ApplyFrom.supplizer.value
            suid = request.user.id

        else:
            tlp_from = ApplyFrom.platform.value

            suid = None
        with db.auto_commit():
            apply_info = TimeLimitedProduct.query.filter_by(TLPid=tlpid, isdelete=False).first_('无此申请记录')

            if apply_info.TLAstatus != ApplyStatus.wait_check.value:
                raise StatusError('只有在审核状态的申请可以撤销')
            if apply_info.SUid != suid:
                raise AuthorityError('仅可撤销自己提交的申请')
            apply_info.TLAstatus = ApplyStatus.cancle.value

            # 获取原商品属性
            # gnap_old = GuessNumAwardProduct.query.filter(GuessNumAwardProduct.GNAAid == apply_info.GNAAid,
            #                                                 GuessNumAwardProduct.isdelete == False).first()
            product = Products.query.filter_by(PRid=apply_info.PRid, PRfrom=tlp_from, isdelete=False).first_('商品信息出错')
            # 获取原sku属性
            tls_list = TimeLimitedSku.query.filter(
                TimeLimitedSku.isdelete == False,
                TimeLimitedSku.TLPid == apply_info.TLPid
            ).all()

            # 遍历原sku 将库存退出去
            for sku in tls_list:
                sku_instance = ProductSku.query.filter_by(
                    isdelete=False, PRid=product.PRid, SKUid=sku.SKUid).first_('商品sku信息不存在')
                self._update_stock(int(sku.TLSstock), product, sku_instance)

            # 同时将正在进行的审批流改为取消 todo
            approval_info = Approval.query.filter_by(
                AVcontent=tlpid, AVstartid=request.user.id, isdelete=False,
                AVstatus=ApplyStatus.wait_check.value).first()
            approval_info.AVstatus = ApplyStatus.cancle.value
            if is_admin():
                BASEADMIN().create_action(AdminActionS.update.value, 'TimeLimitedProduct', tlpid)
        return Success('取消成功', {'tlpid': tlpid})

    def del_award(self):
        """删除申请"""
        if is_supplizer():
            usid = request.user.id
            sup = Supplizer.query.filter_by_(SUid=usid).first_('供应商信息错误')
            suid = sup.SUid
            current_app.logger.info('Supplizer {} delete timelimit apply'.format(sup.SUname))
        elif is_admin():
            usid = request.user.id
            admin = Admin.query.filter_by_(ADid=usid).first_('管理员信息错误')
            current_app.logger.info('Admin {} timelimit apply'.format(admin.ADname))
            sup = None
            suid = None
        else:
            raise AuthorityError()
        data = parameter_required(('tlpid',))
        tlpid = data.get('tlpid')
        with db.auto_commit():
            apply_info = TimeLimitedProduct.query.filter_by(TLPid=tlpid, isdelete=False).first_('无此申请记录')
            # if sup:
            #     assert apply_info.SUid == usid, '供应商只能删除自己提交的申请'
            if apply_info.SUid != suid:
                raise ParamsError('只能删除自己提交的申请')
            if apply_info.TLAstatus not in [ApplyStatus.cancle.value, ApplyStatus.reject.value,
                                            ApplyStatus.shelves.value]:
                raise StatusError('只能删除已拒绝或已撤销状态下的申请')
            apply_info.isdelete = True
            if is_admin():
                BASEADMIN().create_action(AdminActionS.delete.value, 'TimeLimitedProduct', tlpid)

        return Success('删除成功', {'tlpid': tlpid})

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

    def _re_stock(self, tlp):
        """库存回复"""
        apply_skus = TimeLimitedSku.query.filter(
            TimeLimitedSku.isdelete == False,
            TimeLimitedSku.TLPid == tlp.TLPid).all()
        for apply_sku in apply_skus:
            sku = ProductSku.query.filter(ProductSku.SKUid == apply_sku.SKUid).first()
            product = Products.query.filter(Products.PRid == sku.PRid).first()
            # 加库存
            self._update_stock(int(apply_sku.TLSstock), product, sku)

    def _fill_tlp(self, tlp, tla):
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
        # 预计佣金
        comm = Commision.query.filter(Commision.isdelete == False).first()
        try:
            commision = json.loads(comm.Levelcommision)
            level1commision = commision[0]  # 一级分销商
            planetcommision = commision[-1]  # 平台收费比例
        except ValueError:
            current_app.logger.info('ValueError error')
        except IndexError:
            current_app.logger.info('IndexError error')

        preview_get = []
        for tls in tls_list:
            sku = ProductSku.query.filter_by(SKUid=tls.SKUid, isdelete=False).first()
            if not sku:
                current_app.logger.info('该sku已删除 skuid = {0}'.format(tls.SKUid))
                continue
            # sku.hide('SKUprice')
            # sku.hide('SKUstock')
            sku.fill('tlsprice', tls.SKUprice)
            sku.fill('tlsstock', tls.TLSstock)
            preview_get.append(
                self._commision_preview(
                    price=tls.SKUprice,
                    planet_rate=planetcommision,
                    planet_and_user_rate=sku.SkudevideRate or planetcommision,
                    current_user_rate=level1commision
                ))
            if isinstance(sku.SKUattriteDetail, str):
                sku.SKUattriteDetail = json.loads(sku.SKUattriteDetail)
            sku_value_item.append(sku.SKUattriteDetail)
            skus.append(sku)
        product.fill('profict', min(preview_get))
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
        product.fill('tlastarttime', tla.TLAstartTime)
        product.fill('tlaendtime', tla.TLAendTime)
        product.fill('tlpprice', tlp.PRprice)
        product.fill('tlpid', tlp.TLPid)
        product.fill('tlpcreatetime', tlp.createtime)
        product.fill('tlastatus_zh', ApplyStatus(tlp.TLAstatus).zh_value)
        # current_app.logger.info(tlp.TLPid)
        # current_app.logger.info(product.tlpid)
        product.fill('tlastatus_en', ApplyStatus(tlp.TLAstatus).name)
        product.fill('tlastatus', tlp.TLAstatus)
        # product.fill('prprice', tlp.PRprice)

        return product

    def _check_sort(self, sort):
        if not sort:
            return 1
        sort = int(sort)
        count_pc = TimeLimitedActivity.query.filter(TimeLimitedActivity.isdelete == False).count()
        if sort < 1:
            return 1
        if sort > count_pc:
            return count_pc
        return sort

    def _crete_celery_task(self, tlastatus, tlaid, start_time, end_time):
        current_app.logger.info('创建异步任务 tlaid = {} 状态是 {} '.format(tlaid, TimeLimitedStatus(tlastatus).zh_value))
        if tlastatus < TimeLimitedStatus.starting.value:
            current_app.logger.info('开始创建开始活动的异步任务 开始时间是 {}'.format(start_time))
            connid = 'start{}'.format(tlaid)
            self._cancle_celery(connid)
            start_task_id = start_timelimited.apply_async(args=(tlaid,), eta=start_time - timedelta(hours=8))
            conn.set(connid, start_task_id)
        if tlastatus < TimeLimitedStatus.end.value:
            current_app.logger.info('开始创建结束活动的异步任务 结束时间是 {}'.format(end_time))
            connid = 'end{}'.format(tlaid)
            self._cancle_celery(connid)
            end_task_id = end_timelimited.apply_async(args=(tlaid,), eta=end_time - timedelta(hours=8))
            conn.set(connid, end_task_id)

    def _fill_tla(self, time_limited, time_now=datetime.now()):

        time_limited.fill('tlastatus_zh', TimeLimitedStatus(time_limited.TLAstatus).zh_value)
        time_limited.fill('tlastatus_en', TimeLimitedStatus(time_limited.TLAstatus).name)
        tlp_count = TimeLimitedProduct.query.filter(
            TimeLimitedProduct.TLAid == time_limited.TLAid,
            TimeLimitedProduct.isdelete == False,
            TimeLimitedProduct.TLAstatus == ApplyStatus.agree.value
        ).count()
        time_limited.fill('prcount', tlp_count)
        if time_limited.TLAstatus == TimeLimitedStatus.waiting.value:
            if isinstance(time_limited.TLAstartTime, datetime):
                starttime = time_limited.TLAstartTime
            else:
                starttime = datetime.strptime(str(time_limited.TLAstartTime), '%Y-%m-%d %H:%M:%S')
            time_limited.fill('duration_start', str(starttime - time_now))
        if time_limited.TLAstatus == TimeLimitedStatus.starting.value:
            if isinstance(time_limited.TLAendTime, datetime):
                end_time = time_limited.TLAendTime
            else:
                end_time = datetime.strptime(str(time_limited.TLAendTime), '%Y-%m-%d %H:%M:%S')
            time_limited.fill('duration_end', str(end_time - time_now))

    def _cancle_celery(self, conid):
        exist_task = conn.get(conid)
        if exist_task:
            exist_task = str(exist_task, encoding='utf-8')
            current_app.logger.info('已有任务id: {}'.format(exist_task))
            celery.AsyncResult(exist_task).revoke()
