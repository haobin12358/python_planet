import json
import math
import uuid
from datetime import datetime, date, timedelta

from flask import request, current_app

from planet.common.params_validates import parameter_required
from planet.common.success_response import Success
from planet.common.token_handler import token_required, get_current_user, is_supplizer, is_admin, admin_required, \
    common_user
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
        # 根据分类查询
        time_now = datetime.now()
        data = parameter_required()
        tlastatus = data.get('tlastatus')
        kw = data.get('tlaname', '')
        # adid = data.get('adname')
        # tlaid = data.get('tlaid')
        # adname = data.get('adname')
        # tlaname = data.get('tlaname')

        filter_args = {
            TimeLimitedActivity.isdelete == False,
        }
        if common_user():
            filter_args.add(TimeLimitedActivity.TLAendTime >= time_now)
            filter_args.add(TimeLimitedActivity.TLAstatus == TimeLimitedStatus.publish.value)
        else:
            if tlastatus or tlastatus == 0:
                filter_args.add(TimeLimitedActivity.TLAstatus == tlastatus)
            if kw:
                filter_args.add(TimeLimitedActivity.TlAname.ilike('%{}%'.format(kw)))
            # if adname:
            #     filter_args.add(Admin.ADname.ilike('%{}%'.format(adname)))
            # if tlaname:
            #     filter_args.add(TimeLimitedActivity.TlAname.ilike('%{}%'.format(tlaname)))

        # filter_args.add(TimeLimitedActivity.TLAstatus >= TimeLimitedStatus.abort.value)

        time_limited_list = TimeLimitedActivity.query.filter(*filter_args).order_by(
            TimeLimitedActivity.TLAsort.asc(), TimeLimitedActivity.createtime.desc()).all()
        for time_limited in time_limited_list:
            time_limited.fill('tlastatus_zh', TimeLimitedStatus(time_limited.TLAstatus).zh_value)
            time_limited.fill('tlastatus_en', TimeLimitedStatus(time_limited.TLAstatus).name)
            tlp_count = TimeLimitedProduct.query.filter(
                TimeLimitedProduct.TLAid == time_limited.TLAid,
                TimeLimitedProduct.isdelete == False,
                TimeLimitedProduct.TLAstatus == ApplyStatus.agree.value
            ).count()
            time_limited.fill('prcount', tlp_count)

        return Success(data=time_limited_list)

    def list_product(self):
        """获取活动商品"""
        data = parameter_required()
        # tlaid = data.get('tlaid')
        tlastatus = data.get('tlastatus')
        kw = data.get('prtitle', '') # 关键词
        filter_args = {
            TimeLimitedProduct.isdelete == False,
        }
        if common_user():
            filter_args.add(TimeLimitedProduct.TLAstatus == ApplyStatus.agree.value)

        # if tlaid:
        #     filter_args.add(TimeLimitedProduct.TLAid == data.get('tlaid'))
        if tlastatus or tlastatus == 0:
            filter_args.add(TimeLimitedProduct.TLAstatus == data.get('tlastatus'))
        elif kw:
            filter_args.add(Products.PRtitle.ilike('%{}%'.format(kw)))

        tlp_list = TimeLimitedProduct.query.join(Products, Products.PRid == TimeLimitedProduct.PRid).filter(*filter_args).order_by(
            TimeLimitedProduct.createtime.desc()).all()

        product_list = list()
        for tlp in tlp_list:
            tlaid = tlp.TLAid
            tla = TimeLimitedActivity.query.filter(
                TimeLimitedActivity.isdelete == False,
                TimeLimitedActivity.TLAid == tlaid,
                TimeLimitedActivity.TLAstatus == TimeLimitedStatus.publish.value
            ).first_('活动已下架')
            product = self._fill_tlp(tlp, tla)
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
        data = parameter_required(('tlpid',))
        tlp = TimeLimitedProduct.query.filter(TimeLimitedProduct.isdelete == False,
                                              TimeLimitedProduct.TLPid == data.get('tlpid')).first_('活动商品已售空')
        tla = TimeLimitedActivity.query.filter(TimeLimitedActivity.isdelete == False,
                                               TimeLimitedActivity.TLAstatus == TimeLimitedStatus.publish.value,
                                               TimeLimitedActivity.TLAid == tlp.TLAid).first_('活动已结束')
        return Success(data=self._fill_tlp(tlp, tla))

    @token_required
    def add_order(self):
        data = parameter_required(('skuid', 'omclient', 'uaid', 'opaytype', 'tlaid', 'nums'))
        try:
            omclient = int(data.get('omclient', Client.wechat.value))  # 下单设备
            Client(omclient)
        except Exception as e:
            raise ParamsError('客户端或商品来源错误')
        try:
            opaytype = int(data.get('opaytype'))
        except ValueError:
            raise StatusError('支付方式异常, 未创建订单')
        skuid = data.get('skuid')
        uaid = data.get('uaid')
        # 校验活动是否开启
        tla = TimeLimitedActivity.query.filter(
            TimeLimitedActivity.TLAid == data.get('tlaid'), TimeLimitedActivity.isdelete == False,
            TimeLimitedActivity.TLAstatus == TimeLimitedStatus.publish.value).first_('活动不存在')

        now = datetime.now()
        usid = request.user.id
        user = get_current_user()
        tlp = TimeLimitedProduct.query.filter(
            TimeLimitedProduct.isdelete == False,
            TimeLimitedProduct.TLAid == tla.TLAid,
            TimeLimitedProduct.TLPid == TimeLimitedSku.TLPid,
            TimeLimitedSku.SKUid == data.get('skuid')).first_('商品已售空')
        product = self._fill_tlp(tlp, tla)
        product_category = ProductCategory.query.filter_by(PCid=product.PCid).first()
        tls = TimeLimitedSku.query.filter(
            TimeLimitedSku.isdelete == False,
            TimeLimitedSku.TLPid == tlp.TLPid,
            TimeLimitedSku.SKUid == data.get('skuid')
        ).first_('sku 已售罄')
        with db.auto_commit():
            if tls.TLSstock is not None:
                if tls.TLSstock <= 0:
                    raise StatusError('库存不足')
                tls.TLSstock -= 1
            suid = tlp.SUid
            # 地址拼接
            user_address_instance = UserAddress.query.filter_by_({'UAid': uaid, 'USid': usid}).first_('地址信息不存在')
            omrecvphone = user_address_instance.UAphone
            areaid = user_address_instance.AAid
            area, city, province = db.session.query(AddressArea, AddressCity, AddressProvince).filter(
                AddressArea.ACid == AddressCity.ACid, AddressCity.APid == AddressProvince.APid).filter(
                AddressArea.AAid == areaid).first_('地址有误')
            address = getattr(province, "APname", '') + getattr(city, "ACname", '') + getattr(
                area, "AAname", '')
            omrecvaddress = address + user_address_instance.UAtext
            omrecvname = user_address_instance.UAname
            # 创建订单
            omid = str(uuid.uuid1())
            opayno = self.wx_pay.nonce_str
            nums = data.get('nums', 1)
            assert nums > 0
            price = tls.SKUprice * int(nums)
            sku_instance = ProductSku.query.filter(ProductSku.SKUid == tls.SKUid, ProductSku.isdelete == False).first()
            # 如果活动时间未到 使用原价购买
            if now < tla.TLAstartTime:
                price = sku_instance.SKUprice
            # 主单
            order_main_dict = {
                'OMid': omid,
                'OMno': self._generic_omno(),
                'OPayno': opayno,
                'USid': usid,
                'OMfrom': OrderFrom.fresh_man.value,
                'PBname': product.PBname,
                'PBid': product.PBid,
                'OMclient': omclient,
                'OMfreight': 0,  # 运费暂时为0
                'OMmount': price,
                'OMmessage': data.get('ommessage'),
                'OMtrueMount': price,
                # 收货信息
                'OMrecvPhone': omrecvphone,
                'OMrecvName': omrecvname,
                'OMrecvAddress': omrecvaddress,
                'PRcreateId': suid
            }
            order_main_instance = OrderMain.create(order_main_dict)
            db.session.add(order_main_instance)
            # 副单
            order_part_dict = {
                'OPid': str(uuid.uuid1()),
                'OMid': omid,
                'SKUid': skuid,
                'PRid': product.PRid,
                'PRattribute': product.PRattribute,
                'SKUattriteDetail': product.SKUattriteDetail,
                'SKUprice': price,
                'PRtitle': product.PRtitle,
                'SKUsn': sku_instance.SKUsn,
                'PCname': product_category.PCname,
                'PRmainpic': product.PRmainpic,
                'OPnum': 1,
                # # 副单商品来源
                'PRfrom': product.PRfrom,
                'UPperid': getattr(user, 'USsupper1', ''),
                'UPperid2': getattr(user, 'USsupper2', ''),
                'UPperid3': getattr(user, 'USsupper3', ''),
                'USCommission1': getattr(user, 'USCommission1', ''),
                'USCommission2': getattr(user, 'USCommission2', ''),
                'USCommission3': getattr(user, 'USCommission3', '')
            }
            order_part_instance = OrderPart.create(order_part_dict)
            db.session.add(order_part_instance)
            # 支付数据表
            order_pay_dict = {
                'OPayid': str(uuid.uuid1()),
                'OPayno': opayno,
                'OPayType': opaytype,
                'OPayMount': price,
            }
            order_pay_instance = OrderPay.create(order_pay_dict)
            db.session.add(order_pay_instance)
        from planet.extensions.tasks import auto_cancle_order

        auto_cancle_order.apply_async(args=([omid],), countdown=30 * 60, expires=40 * 60, )
        # 生成支付信息
        body = product.PRtitle
        current_user = get_current_user()
        openid = current_user.USopenid1 or current_user.USopenid2
        pay_args = self._pay_detail(omclient, opaytype, opayno, float(price), body, openid=openid)
        response = {
            'pay_type': PayType(opaytype).name,
            'opaytype': opaytype,
            'args': pay_args
        }
        return Success('创建订单成功', data=response)

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
            'TLAsort': 0,
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
            tla = TimeLimitedActivity.query.filter(TimeLimitedActivity.isdelete == False,
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

        # todo  添加到审批流
        super(CTimeLimited, self).create_approval('totimelimited', request.user.id, tlp.TLPid, applyfrom=tlp_from)
        return Success('申请成功', {'tlpid': tlp.TLPid})

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
        with db.auto_commit():
            # 获取申请单
            apply_info = TimeLimitedProduct.query.filter(
                TimeLimitedProduct.TLPid == data.get('tlpid'),
                TimeLimitedProduct.PRid == data.get('prid'),
                TimeLimitedProduct.isdelete == False
            ).first_('商品不存在')
            if apply_info.TLAstatus not in [ApplyStatus.reject.value, ApplyStatus.cancle.value]:
                raise ParamsError('只有已拒绝或撤销状态的申请可以进行修改')
            if apply_info.SUid != suid:
                raise AuthorityError('仅可修改自己提交的申请')
            # if is_admin() and apply_info.SUid:
            #     raise AuthorityError('仅可修改自己提交的申请')

            product = Products.query.filter(*filter_args).first_('商品未上架')
            # instance_list = list()
            skus = data.get('skus')
            tla = TimeLimitedActivity.query.filter(
                TimeLimitedActivity.isdelete == False,
                TimeLimitedActivity.TLAid == data.get('tlaid')).first_('活动已停止报名')
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

        super(CTimeLimited, self).create_approval('totimelimited', request.user.id, apply_info.TLPid, applyfrom=tlp_from)
        return Success('修改成功')

    @admin_required
    def update_activity(self):
        data = parameter_required(('tlaid',))
        with db.auto_commit():
            tla = TimeLimitedActivity.query.filter(TimeLimitedActivity.TLAid == data.get('tlaid'),
                                                   TimeLimitedActivity.isdelete == False).first_('活动已删除')
            if data.get('delete'):
                tla.isdelete = True
                tlp_list = TimeLimitedProduct.query.filter(TimeLimitedProduct.isdelete == False,
                                                           TimeLimitedProduct.TLAid == tla.TLAid).all()
                # 如果删除活动的话，退还库存
                for tlp in tlp_list:
                    self._re_stock(tlp)
                return Success('删除成功')

            for k in tla.keys():
                if k == 'TLAid' or k == 'isdelete':
                    continue
                low_k = str(k).lower()
                value = data.get(low_k)
                if  value or value == 0:
                    if k == 'TLAstatus':
                        try:
                            TimeLimitedStatus(value)
                        except:
                            continue
                    if k == 'TLAsort':
                        value = self._check_sort(value)
                    tla.__setattr__(k, value)
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
            if apply_info.SUid !=suid:
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
        return Success('取消成功', {'tlpid': tlpid})

    def del_award(self):
        """删除申请"""
        if is_supplizer():
            usid = request.user.id
            sup = Supplizer.query.filter_by_(SUid=usid).first_('供应商信息错误')
            suid = sup.SUid
            current_app.logger.info('Supplizer {} delete guessnum apply'.format(sup.SUname))
        elif is_admin():
            usid = request.user.id
            admin = Admin.query.filter_by_(ADid=usid).first_('管理员信息错误')
            current_app.logger.info('Admin {} guessnum apply'.format(admin.ADname))
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
            if apply_info.TLAstatus not in [ApplyStatus.cancle.value, ApplyStatus.reject.value, ApplyStatus.shelves.value]:
                raise StatusError('只能删除已拒绝或已撤销状态下的申请')
            apply_info.isdelete = True

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
        for tls in tls_list:
            sku = ProductSku.query.filter_by(SKUid=tls.SKUid, isdelete=False).first()
            if not sku:
                current_app.logger.info('该sku已删除 skuid = {0}'.format(tls.SKUid))
                continue
            # sku.hide('SKUprice')
            # sku.hide('SKUstock')
            sku.fill('tlsprice', tls.SKUprice)
            sku.fill('tlsstock', tls.TLSstock)

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
        product.fill('tlastarttime', tla.TLAstartTime)
        product.fill('tlaendtime', tla.TLAendTime)
        product.fill('tlpprice', tlp.PRprice)
        product.fill('tlpid', tlp.TLPid)
        product.fill('tlpcreatetime', tlp.createtime)
        product.fill('tlastatus_zh', ApplyStatus(tlp.TLAstatus).zh_value)
        product.fill('tlastatus_en', ApplyStatus(tlp.TLAstatus).name)
        product.fill('tlastatus', tlp.TLAstatus)

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
