import json
import uuid
from datetime import datetime, date, timedelta

from flask import request, current_app

from planet.common.params_validates import parameter_required
from planet.common.success_response import Success
from planet.common.token_handler import token_required, get_current_user, is_supplizer, is_admin
from planet.config.enums import ApplyStatus, OrderMainStatus, OrderFrom, Client, ActivityType, PayType, ProductStatus, \
    ApplyFrom
from planet.common.error_response import StatusError, ParamsError, AuthorityError
from planet.control.BaseControl import BASEAPPROVAL
from planet.control.COrder import COrder
from planet.extensions.register_ext import db
from planet.extensions.validates.activty import ListFreshmanFirstOrderApply, ShelfFreshManfirstOrder
from planet.models import FreshManFirstApply, Products, FreshManFirstProduct, FreshManFirstSku, ProductSku, \
    ProductSkuValue, OrderMain, Activity, UserAddress, AddressArea, AddressCity, AddressProvince, OrderPart, OrderPay, \
    FreshManJoinFlow, ProductMonthSaleValue, ProductImage, ProductBrand, Supplizer, Admin, Approval
from .CUser import CUser


class CFreshManFirstOrder(COrder, CUser):

    def list(self):
        """获取列表"""
        time_now = datetime.now()
        fresh_man_products = FreshManFirstProduct.query.join(
            FreshManFirstApply, FreshManFirstApply.FMFAid == FreshManFirstProduct.FMFAid
        ).filter_(
            FreshManFirstApply.FMFAstatus == ApplyStatus.agree.value,
            FreshManFirstApply.AgreeStartime <= time_now,
            FreshManFirstApply.AgreeEndtime >= time_now,
            FreshManFirstApply.isdelete == False,
            FreshManFirstProduct.isdelete == False,
            Products.PRid == FreshManFirstProduct.PRid,
            Products.isdelete == False,
        ).all()
        for fresh_man_product in fresh_man_products:
            fresh_man_product.hide('PRattribute', 'PRid', 'PBid', )
        # 上方图
        activity = Activity.query.filter_by_({
            'ACtype': ActivityType.fresh_man.value,
            'ACshow': True
        }).first_('活动已结束')
        data = {
            'fresh_man': fresh_man_products,
            'actopPic': activity['ACtopPic'],
            'acdesc': activity.ACdesc,
            'acname': activity.ACname,
        }
        return Success(data=data)

    def get(self):
        """获取单个新人商品"""
        data = parameter_required(('fmfpid', ))
        fmfpid = data.get('fmfpid')
        fresh_man_first_product = FreshManFirstProduct.query.filter_by_({
            'FMFPid': fmfpid
        }).first_('商品不存在')
        #
        prid = fresh_man_first_product.PRid
        product = Products.query.filter_by_({'PRid': prid}).first_()  # 商品已删除未处理
        product.PRfeight = fresh_man_first_product.PRfeight
        product.PRattribute = json.loads(product.PRattribute)
        product.PRtitle = fresh_man_first_product.PRtitle
        # 新人商品sku
        fresh_man_skus = FreshManFirstSku.query.filter_by_({'FMFPid': fmfpid}).all()

        product_skus = []  # sku对象
        sku_value_item = []
        for fresh_man_sku in fresh_man_skus:
            product_sku = ProductSku.query.filter_by({'SKUid': fresh_man_sku.SKUid}).first()
            product_sku.SKUprice = fresh_man_sku.SKUprice
            product_skus.append(product_sku)
            product_sku.SKUattriteDetail = json.loads(product_sku.SKUattriteDetail)
            sku_value_item.append(product_sku.SKUattriteDetail)  # 原商品的sku
        product.fill('skus', product_skus)

        # 是否有skuvalue, 如果没有则自行组装(这个sku_value是商品的sku_value, 而不再单独设置新人商品的sku)
        sku_value_instance = ProductSkuValue.query.filter_by_({
            'PRid': prid
        }).first()
        # todo 合理的显示sku
        # if not sku_value_instance:
        sku_value_item_reverse = []
        for index, name in enumerate(product.PRattribute):
            value = list(set([attribute[index] for attribute in sku_value_item]))
            value = sorted(value)
            temp = {
                'name': name,
                'value': value
            }
            sku_value_item_reverse.append(temp)
        # else:
        #     sku_value_item_reverse = []  # 转置
        #     pskuvalue = json.loads(sku_value_instance.PSKUvalue)
        #     for index, value in enumerate(pskuvalue):
        #         sku_value_item_reverse.append({
        #             'name': product.PRattribute[index],
        #             'value': value
        #         })

        product.fill('SkuValue', sku_value_item_reverse)
        # 轮播图
        images = ProductImage.query.filter_by_({'PRid': prid}). \
            order_by(ProductImage.PIsort).all()
        product.fill('image', images)
        # 月销量
        month_sale_instance = ProductMonthSaleValue.query.filter_by_({'PRid': prid}).first()
        month_sale_value = getattr(month_sale_instance, 'PMSVnum', 0)
        product.fill('month_sale_value', month_sale_value)
        # 品牌
        product.fill('brand', {
            'pbname': fresh_man_first_product.PBname
        })

        return Success(data=product)

    @token_required
    def add_order(self):
        """购买, 返回支付参数"""
        data = parameter_required(('skuid', 'omclient', 'uaid', 'opaytype'))
        try:
            omclient = int(data.get('omclient', Client.wechat.value))  # 下单设备
            Client(omclient)
        except Exception as e:
            raise ParamsError('客户端或商品来源错误')
        # 只可以买一次
        usid = request.user.id
        exists_order = OrderMain.query.filter(
            OrderMain.USid == usid,
            OrderMain.OMstatus > OrderMainStatus.wait_pay.value
        ).first()
        if exists_order:
            raise StatusError('您不是新人')
        try:
            opaytype = int(data.get('opaytype'))
        except ValueError:
            raise StatusError('支付方式异常, 未创建订单')
        skuid = data.get('skuid')
        uaid = data.get('uaid')
        # 该sku是否是活动sku
        today = date.today()
        # 新人商品sku
        fresh_man_sku = FreshManFirstSku.query.join(
            FreshManFirstProduct, FreshManFirstSku.FMFPid == FreshManFirstProduct.FMFPid
        ).join(FreshManFirstApply, FreshManFirstApply.FMFAid == FreshManFirstProduct.FMFAid).filter(
            FreshManFirstApply.FMFAstatus == ApplyStatus.agree.value,
            FreshManFirstApply.AgreeStartime <= today,
            FreshManFirstApply.AgreeEndtime >= today,
            FreshManFirstSku.isdelete == False,
            FreshManFirstProduct.isdelete == False,
            FreshManFirstApply.isdelete == False,
            FreshManFirstSku.SKUid == skuid,
        ).first_('当前商品未在活动中')

        with db.auto_commit():
            if fresh_man_sku.FMFPstock is not None:
                if fresh_man_sku.FMFPstock < 0:
                    raise StatusError('库存不足')
                fresh_man_sku.FMFPstock -= 1
                db.session.add(fresh_man_sku)
            Activity.query.filter_by_({
                'ACtype': ActivityType.fresh_man.value,
                'ACshow': True
            }).first_('活动未在进行')
            # 新人商品
            fresh_first_product = FreshManFirstProduct.query.filter_by_({
                'FMFPid': fresh_man_sku.FMFPid
            }).first_('当前商品未在活动中')
            # sku详情
            product_sku = ProductSku.query.filter_by_({
                'SKUid': skuid
            }).first_('商品属性已删除')
            # 商品详情
            product_instance = Products.query.filter_by({
                'PRid': fresh_first_product.PRid
            }).first_('商品已删除')
            # 活动申请详情
            fresh_first_apply = FreshManFirstApply.query.filter(
                FreshManFirstApply.isdelete == False,
                FreshManFirstApply.FMFAid == fresh_first_product.FMFAid,
            ).first_('活动不存在')
            suid = fresh_first_apply.SUid if fresh_first_apply.FMFAfrom else None
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
            # 判断是否是别人分享而来
            secret_usid = data.get('secret_usid')
            if secret_usid:
                try:
                    from_usid = self._base_decode(secret_usid)
                    # 来源用户是否购买
                    from_user_order = OrderMain.query.filter_by().filter(
                        OrderMain.USid == from_usid,
                        OrderMain.OMstatus > OrderMainStatus.wait_pay.value,
                        OrderMain.OMfrom == OrderFrom.fresh_man.value,
                    ).first()
                except ValueError:
                    current_app.logger.info('secret_usid decode error : {}'.format(secret_usid))
                    from_user_order = None
            else:
                from_user_order = None

            # 创建订单
            omid = str(uuid.uuid1())
            opayno = self.wx_pay.nonce_str
            price = fresh_man_sku.SKUprice
            # 主单
            order_main_dict = {
                'OMid': omid,
                'OMno': self._generic_omno(),
                'OPayno': opayno,
                'USid': usid,
                'OMfrom': OrderFrom.fresh_man.value,
                'PBname': fresh_first_product.PBname,
                'PBid': fresh_first_product.PBid,
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
                'OMid': omid,
                'OPid': str(uuid.uuid1()),
                'SKUid': skuid,
                'PRattribute': fresh_first_product.PRattribute,
                'SKUattriteDetail': product_sku.SKUattriteDetail,
                'PRtitle': fresh_first_product.PRtitle,
                'SKUprice': price,
                'PRmainpic': fresh_first_product.PRmainpic,
                'OPnum': 1,
                'PRid': fresh_first_product.PRid,
                # # 副单商品来源
                'PRfrom': product_instance.PRfrom,
                # 'PRcreateId': product_instance.CreaterId
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
            # 新人首单参与记录
            fresh_man_join_dict = {
                'FMJFid': str(uuid.uuid1()),
                'OMid': omid,
                'OMprice': price
            }
            if from_user_order:
                fresh_man_join_dict['UPid'] = from_usid
            join_instance = FreshManJoinFlow.create(fresh_man_join_dict)
            db.session.add(join_instance)
            # 删除未支付的新人订单
            if exists_order:
                exists_order.isdelete = True
                db.session.add(exists_order)
        # 生成支付信息
        body = product_instance.PRtitle
        current_user = get_current_user()
        openid = current_user.USopenid1 or current_user.USopenid2
        pay_args = self._pay_detail(omclient, opaytype, opayno, float(price), body, openid=openid)
        response = {
            'pay_type': PayType(opaytype).name,
            'opaytype': opaytype,
            'args': pay_args
        }
        return Success('创建订单成功', data=response)

    def apply_award(self):
        """申请添加奖品"""
        if not (is_supplizer() or is_admin()):
            raise AuthorityError()
        data = parameter_required(('prid', 'fmfaendtime', 'fmfastarttime', 'prprice', 'skus'))
        prid = data.get('prid')
        apply_from = ApplyFrom.supplizer.value if is_supplizer() else ApplyFrom.platform.value
        product = Products.query.filter(Products.PRid == prid, Products.isdelete == False,
                                    Products.PRstatus.in_([ProductStatus.usual.value, ProductStatus.auditing.value])
                                  ).first_('当前商品状态不允许进行申请')
        product_brand = ProductBrand.query.filter(ProductBrand.PBid == product.PBid).first_('商品所在信息不全')
        # 将申请事物时间分割成每天单位
        with db.auto_commit():
            fresh_first_apply = FreshManFirstApply.create({
                'FMFAid': str(uuid.uuid1()),
                'SUid': request.user.id,
                'FMFAstartTime': data.get('fmfastarttime'),
                'FMFAendTime': data.get('fmfaendtime'),
                'FMFAfrom': apply_from,
                'AgreeStartime': data.get('fmfastarttime'),
                'AgreeEndtime': data.get('fmfaendtime'),
            })
            db.session.add(fresh_first_apply)
            # 商品, 暂时只可以添加一个商品
            fresh_first_product = FreshManFirstProduct.create({
                'FMFPid': str(uuid.uuid1()),
                'FMFAid': fresh_first_apply.FMFAid,
                'PRid': prid,
                'PRmainpic': product.PRmainpic,
                'PRtitle': product.PRtitle,
                'PBid': product.PBid,
                'PBname': product_brand.PBname,
                'PRattribute': product.PRattribute,
                'PRdescription': product.PRdescription,
                'PRprice': data.get('prprice')
            })
            db.session.add(fresh_first_product)
            skus = data.get('skus')
            for sku in skus:
                skuid = sku.get('skuid')
                skuprice = sku.get('skuprice')
                skustock = sku.get('skustock')
                sku_instance = ProductSku.query.filter(
                    ProductSku.isdelete == False,
                    ProductSku.PRid == prid,
                    ProductSku.SKUid == skuid
                ).first_('商品sku信息不存在')
                self._update_stock(-int(skustock), product, sku_instance)
                fresh_first_sku = FreshManFirstSku.create({
                    'FMFSid': str(uuid.uuid1()),
                    'FMFPid': fresh_first_product.FMFPid,
                    'FMFPstock': skustock,
                    'SKUid': skuid,
                    'SKUprice': float(skuprice),
                })
                db.session.add(fresh_first_sku)
        BASEAPPROVAL().create_approval('tofreshmanfirstproduct', request.user.id,
                                       fresh_first_apply.FMFAid, apply_from)
        return Success('申请添加成功', data=fresh_first_apply.FMFAid)

    def update_award(self):
        """修改"""
        if not (is_supplizer() or is_admin()):
            raise AuthorityError()
        data = parameter_required(('prid', 'prprice', 'skus', 'fmfaid'))
        prid = data.get('prid')
        fmfaid = data.get('fmfaid')
        apply_from = ApplyFrom.supplizer.value if is_supplizer() else ApplyFrom.platform.value
        product = Products.query.filter(Products.PRid == prid, Products.isdelete == False,
                                    Products.PRstatus.in_([ProductStatus.usual.value, ProductStatus.auditing.value])
                                  ).first_('当前商品状态不允许进行申请')
        product_brand = ProductBrand.query.filter(ProductBrand.PBid == product.PBid).first_('商品所在信息不全')
        with db.auto_commit():
            fresh_first_apply = FreshManFirstApply.query.filter(FreshManFirstApply.FMFAid == fmfaid,
                                                                FreshManFirstApply.isdelete == False).first_('申请单不存在')
            fresh_first_apply.update({
                'SUid': request.user.id,
                'FMFAfrom': apply_from,
                'FMFAstatus': ApplyStatus.wait_check.value
            })
            db.session.add(fresh_first_apply)
            # 商品, 暂时只可以添加一个商品
            fresh_first_product = FreshManFirstProduct.query.filter(
                FreshManFirstProduct.isdelete == False,
                FreshManFirstProduct.FMFAid == fmfaid,
                FreshManFirstProduct.PRid == prid,
            ).first()
            if not fresh_first_product:
                # 如果没有查找到, 则说明是更换了参与商品, 因此删除旧的
                FreshManFirstProduct.query.filter(FreshManFirstProduct.FMFAid == fmfaid).delete_()
                fresh_first_product = FreshManFirstProduct()
                fresh_first_product.FMFPid = str(uuid.uuid1())
            fresh_first_product = fresh_first_product.update({
                # 'FMFAid': fresh_first_apply.FMFAid,
                'PRid': prid,
                'PRmainpic': product.PRmainpic,
                'PRtitle': product.PRtitle,
                'PBid': product.PBid,
                'PBname': product_brand.PBname,
                'PRattribute': product.PRattribute,
                'PRdescription': product.PRdescription,
                'PRprice': data.get('prprice')
            })
            db.session.add(fresh_first_product)
            skus = data.get('skus')
            skuids = []
            for sku in skus:
                skuid = sku.get('skuid')
                skuids.append(skuid)
                skuprice = sku.get('skuprice')
                skustock = sku.get('skustock')
                sku = ProductSku.query.filter(
                    ProductSku.isdelete == False,
                    ProductSku.PRid == prid,
                    ProductSku.SKUid == skuid
                ).first_('商品sku信息不存在')
                fresh_first_sku = FreshManFirstSku.query.filter(
                    FreshManFirstApply.isdelete == False,
                    FreshManFirstSku.FMFPid == fresh_first_product.FMFPid,
                    FreshManFirstSku.SKUid == skuid
                ).first()
                self._update_stock(fresh_first_apply.FMFPstock - int(skustock), product, sku)
                if not fresh_first_sku:
                    fresh_first_sku = FreshManFirstSku()
                    fresh_first_sku.FMFSid = str(uuid.uuid1())
                fresh_first_sku.update({
                    'FMFSid': str(uuid.uuid1()),
                    'FMFPid': fresh_first_product.FMFPid,
                    'FMFPstock': skustock,
                    'SKUid': skuid,
                    'SKUprice': float(skuprice),
                })
                db.session.add(fresh_first_sku)
                # self._update_stock()
            # 删除其他的不需要的新人首单sku
            FreshManFirstSku.query.filter(
                FreshManFirstSku.isdelete == False,
                FreshManFirstSku.FMFPid == fresh_first_product.FMFPid,
                FreshManFirstSku.SKUid.notin_(skuids)
            ).delete_(synchronize_session=False)

        Approval.query.filter(
            Approval.isdelete == False,
            Approval.AVcontent == fmfaid
        ).delete_()
        BASEAPPROVAL().create_approval('tofreshmanfirstproduct', request.user.id,
                                       fresh_first_apply.FMFAid, apply_from)
        return Success('申请单修改成功', data=fresh_first_apply.FMFAid)

    def award_detail(self):
        """查看申请详情"""
        data = parameter_required(('fmfaid', ))
        fmfaid = data.get('fmfaid')
        apply = FreshManFirstApply.query.filter(FreshManFirstApply.isdelete == False, FreshManFirstApply.FMFAid == fmfaid).first_('该申请不存在')
        apply.fill('FMFAstatus_zh', ApplyStatus(apply.FMFAstatus).zh_value)
        if apply.FMFAfrom == ApplyFrom.platform.value:
            admin = Admin.query.filter(Admin.ADid == apply.SUid).first()
            admin.hide('ADfirstpwd', 'ADpassword')
            apply.fill('from_admin', admin)
        else:
            supplizer = Supplizer.query.filter(Supplizer.SUid == apply.SUid).first()
            supplizer.hide('SUpassword')
            apply.fill('from_supplizer', supplizer)
        apply_product = FreshManFirstProduct.query.filter(FreshManFirstProduct.FMFAid == apply.FMFAid).first()
        apply_product.PRattribute = json.loads(apply_product.PRattribute)
        apply.fill('product', apply_product)
        apply_skus = FreshManFirstSku.query.filter(FreshManFirstSku.FMFPid == apply_product.FMFPid).all()
        for apply_sku in apply_skus:
            sku = ProductSku.query.filter(ProductSku.SKUid == apply_sku.SKUid).first()
            sku.SKUattriteDetail = json.loads(sku.SKUattriteDetail)
            apply_product.fill('apply_sku', apply_sku)
            apply_sku.fill('sku', sku)
        return Success('获取成功', apply)

    def list_apply(self):
        """查看申请列表"""
        if not is_supplizer() and not is_admin():
            raise AuthorityError()
        form = ListFreshmanFirstOrderApply().valid_data()
        suid = form.suid.data
        if is_supplizer():
            suid = request.user.id
        adid = form.adid.data
        status = form.status.data
        query = FreshManFirstApply.query.filter(FreshManFirstApply.isdelete == False)
        if suid:
            query = query.filter(FreshManFirstApply.SUid == suid,
                                 FreshManFirstApply.FMFAfrom == 0)
        if adid:
            query = query.filter(FreshManFirstApply.SUid == adid,
                                 FreshManFirstApply.FMFAfrom == 1)
        if status is not None:
            query = query.filter(FreshManFirstApply.FMFAstatus == status)
        applys = query.order_by(FreshManFirstApply.createtime.desc()).all_with_page()
        for apply in applys:
            # 状态中文
            apply.fill('FMFAstatus_zh', ApplyStatus(apply.FMFAstatus).zh_value)
            # 商品
            fresh_product = FreshManFirstProduct.query.filter(
                FreshManFirstProduct.isdelete == False,
                FreshManFirstProduct.FMFAid == apply.FMFAid,
            ).first()
            apply.fill('fresh_product', fresh_product)
            # 活动sku
            freshsku = FreshManFirstSku.query.filter(
                FreshManFirstSku.isdelete == False,
                FreshManFirstSku.FMFPid == fresh_product.FMFPid
            ).all()
            fresh_product.fill('sku', freshsku)
            # 申请人
            if apply.FMFAfrom == ApplyFrom.supplizer.value:
                supplizer = Supplizer.query.filter(Supplizer.SUid == apply.SUid).first()
                apply.fill('from_supplizer', supplizer)
            elif apply.FMFAfrom == ApplyFrom.platform.value:
                admin = Admin.query.filter(Admin.ADid == apply.SUid).first()
                admin.hide('ADfirstpwd', 'ADpassword')
                apply.fill('from_admin', admin)
        return Success(data=applys)

    def shelf_award(self):
        """撤销申请"""
        if not is_supplizer() and not is_admin():
            raise AuthorityError()
        form = ShelfFreshManfirstOrder().valid_data()
        fmfaid = form.fmfaid.data
        with db.auto_commit():
            suid = request.user.id if is_supplizer() else None
            apply_query = FreshManFirstApply.query.filter(
                FreshManFirstApply.isdelete == False,
                FreshManFirstApply.FMFAid == fmfaid,
                FreshManFirstApply.FMFAstatus == ApplyStatus.wait_check.value
            )
            if suid:
                apply_query = apply_query.filter(
                    FreshManFirstApply.SUid == request.user.id,
                )
            apply = apply_query.first_('申请已处理')
            # 库存处理
            self._re_stock(apply)
            apply.FMFAstatus = ApplyStatus.cancle.value
            db.session.add(apply)
            # 相应的审批流
            Approval.query.filter(
                Approval.isdelete == False,
                Approval.AVcontent == fmfaid
            ).update({
                'AVstatus': ApplyStatus.cancle.value
            })
        return Success('撤销成功')

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
        apply_sku = FreshManFirstSku.query.join(
            FreshManFirstProduct, FreshManFirstProduct.FMFPid == FreshManFirstSku.FMFPid
        ).filter(
            FreshManFirstProduct.FMFAid == apply.FMFAid
        ).first()
        sku = ProductSku.query.filter(
            ProductSku.SKUid == apply_sku.SKUid
        ).first()
        product = Products.query.filter(
            Products.PRid == sku.PRid
        )
        # 加库存
        self._update_stock(apply_sku.FMFPstock, product, sku)

    def _update_stock(self, old_new, product, sku):
        if not old_new:
            return
        current_app.logger.info(product.PRstocks)
        product.PRstocks = product.PRstocks + old_new
        sku.SKUstock += sku.SKUstock + old_new
        current_app.logger.info(product.PRstocks)
        if product.PRstocks < 0:
            raise StatusError('商品库存不足')
        if product.PRstocks and product.PRstatus == ProductStatus.sell_out.value:
            product.PRstatus = ProductStatus.usual.value
        if product.PRstocks == 0:
            product.PRstatus = ProductStatus.sell_out.value
        db.session.add(sku)
        db.session.add(product)

