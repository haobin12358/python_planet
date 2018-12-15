import json
import uuid
from datetime import datetime, date

from flask import request, current_app

from planet.common.params_validates import parameter_required
from planet.common.success_response import Success
from planet.common.token_handler import token_required, get_current_user
from planet.config.enums import ApplyStatus, OrderMainStatus, OrderFrom, Client, ActivityType, PayType
from planet.common.error_response import StatusError, ParamsError
from planet.control.COrder import COrder
from planet.extensions.register_ext import db
from planet.models import FreshManFirstApply, Products, FreshManFirstProduct, FreshManFirstSku, ProductSku, \
    ProductSkuValue, OrderMain, Activity, UserAddress, AddressArea, AddressCity, AddressProvince, OrderPart, OrderPay, \
    FreshManJoinFlow, ProductMonthSaleValue, ProductImage
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
        with db.auto_commit():
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

