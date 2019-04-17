# -*- coding: utf-8 -*-
import json
import uuid
from decimal import Decimal
from datetime import datetime, date, timedelta

from flask import request, current_app
from sqlalchemy import cast, Date, extract
from planet.extensions.register_ext import alipay, wx_pay
from planet.common.error_response import StatusError, ParamsError, NotFound, AuthorityError
from planet.common.params_validates import parameter_required
from planet.common.success_response import Success
from planet.common.token_handler import token_required, get_current_user, is_supplizer, is_admin
from planet.control.BaseControl import BASEAPPROVAL
from planet.extensions.register_ext import db
from planet.extensions.validates.activty import GuessNumCreateForm, GuessNumGetForm, GuessNumHistoryForm
from planet.models import GuessNum, CorrectNum, ProductSku, ProductItems, GuessAwardFlow, Products, ProductBrand, \
    UserAddress, AddressArea, AddressCity, AddressProvince, OrderMain, OrderPart, OrderPay, GuessNumAwardApply, \
    ProductSkuValue, ProductImage, Approval, Supplizer, Admin, OutStock, ProductCategory, GuessNumAwardProduct, \
    GuessNumAwardSku, User, Activity
from planet.config.enums import ActivityRecvStatus, OrderFrom, Client, PayType, ProductStatus, GuessNumAwardStatus, \
    ApprovalType, ApplyStatus, ApplyFrom, ActivityType, HistoryStatus
from .COrder import COrder


class CGuessNum(COrder, BASEAPPROVAL):

    @token_required
    def creat(self):
        # todo 修改具体内容
        """参与活动"""
        date_now = datetime.now()
        if date_now.hour == 14 and date_now.minute > 50:
                raise StatusError('15点以后不开放')
        if date_now.hour > 15:
            raise StatusError('15点以后不开放')
        if date_now.weekday() in [0, 6]:
            raise StatusError('周六周日不开放')
        form = GuessNumCreateForm().valid_data()
        gnnum = form.gnnum.data
        usid = request.user.id

        with db.auto_commit():
            today = date.today()

            today_raward = GuessNumAwardApply.query.filter_by_().filter_(
                GuessNumAwardApply.AgreeStartime <= today,
                GuessNumAwardApply.AgreeEndtime >= today,
                GuessNumAwardApply.GNAAstatus == ApplyStatus.agree.value,
            ).first_('今日活动不开放')

            guess_instance = GuessNum.create({
                'GNid': str(uuid.uuid1()),
                'GNnum': gnnum,
                'USid': usid
            })
            db.session.add(guess_instance)
        return Success('参与成功')

    @token_required
    def get(self):
        """获得单日个人参与"""
        # todo 修改字段
        form = GuessNumGetForm().valid_data()
        usid = request.user.id
        join_history = GuessNum.query.filter_(
            GuessNum.USid == usid,
            cast(GuessNum.createtime, Date) == form.date.data.date(),
            GuessNum.isdelete == False
        ).first_()
        if not join_history:
            if form.date.data.date() == date.today():
                return Success('今日未参与')
            elif form.date.data.date() == date.today() - timedelta(days=1):
                raise NotFound('昨日未参与')
            else:
                raise NotFound('未参与')
        if join_history:
            # todo 换一种查询方式, 不使用日期筛选, 而使用gnnaid筛选
            correct_num = CorrectNum.query.filter(
                CorrectNum.CNdate == join_history.GNdate
            ).first()
            join_history.fill('correct_num', correct_num)
            if not correct_num:
                result = 'not_open'
            else:
                correct_num.hide('CNid')
                if correct_num.CNnum.strip('0') == join_history.GNnum.strip('0'):
                    result = 'correct'
                else:
                    result = 'uncorrect'
            join_history.fill('result', result).hide('USid', 'PRid')

            # product = Products.query.filter_by_({'PRid': join_history.PRid}).first()
            # product.fields = ['PRid', 'PRmainpic', 'PRtitle']
            # join_history.fill('product', product)
        return Success(data=join_history)

    @token_required
    def history_join(self):
        """获取历史参与记录"""
        # todo 修改字段
        form = GuessNumHistoryForm().valid_data()
        year = form.year.data
        month = form.month.data
        try:
            year_month = datetime.strptime(year + '-' + month,  '%Y-%m')
        except ValueError as e:
            raise ParamsError('时间参数异常')
        usid = request.user.id
        join_historys = GuessNum.query.filter(
            extract('month', GuessNum.GNdate) == year_month.month,
            extract('year', GuessNum.GNdate) == year_month.year,
            GuessNum.USid == usid
        ).order_by(GuessNum.GNdate.desc()).group_by(GuessNum.GNdate).all()
        correct_count = 0  # 猜对次数
        today = date.today()
        for join_history in join_historys:
            correct_num = CorrectNum.query.filter(
                CorrectNum.CNdate == join_history.GNdate
            ).first()
            join_history.fill('correct_num', correct_num)
            if not correct_num:
                result = 'not_open'
            else:
                correct_num.hide('CNid')
                if correct_num.CNnum.strip('0') == join_history.GNnum.strip('0'):
                    result = 'correct'
                    correct_count += 1
                else:
                    result = 'uncorrect'
            join_history.fill('result', result).hide('USid', 'PRid')
            if join_history.GNdate < today:
                history_status = HistoryStatus.invalid.value
                history_status_zh = HistoryStatus.invalid.zh_value
            else:
                gn = GuessNum.query.filter_by(USid=request.user.id).order_by(GuessNum.createtime.desc()).first()
                if gn and gn.GNdate == today and (gn.PRid or gn.SKUid or gn.Price):
                    history_status = HistoryStatus.bought.value
                    history_status_zh = HistoryStatus.bought.zh_value
                else:
                    history_status = HistoryStatus.normal.value
                    history_status_zh = HistoryStatus.normal.zh_value

            product = Products.query.filter_by_({'PRid': join_history.PRid}).first()
            product.fields = ['PRid', 'PRmainpic', 'PRtitle']
            join_history.fill('product', product)
            join_history.fill('historystatus', history_status)
            join_history.fill('historystatus_zh', history_status_zh)
        return Success(data=join_historys).get_body(correct_count=correct_count)

    @token_required
    def recv_award(self):
        # 猜数字下单接口
        data = parameter_required(('prid', 'skuid', 'omclient', 'gnaaid', 'uaid', 'opaytype'))
        omid = str(uuid.uuid1())
        # 生成订单
        with db.auto_commit():
            gn = GuessNum.query.filter_by(USid=request.user.id).order_by(GuessNum.createtime.desc()).first()
            now = datetime.now()
            gnaa = GuessNumAwardApply.query.filter_by(GNAAid=data.get('gnaaid'), isdelete=False).first_('参数异常')
            gnap = GuessNumAwardProduct.query.filter_by(
                GNAAid=data.get('gnaaid'), PRid=data.get('prid'), isdelete=False).first_('参数异常')
            gnas = GuessNumAwardSku.query.filter(
                GuessNumAwardSku.GNAPid == gnap.GNAPid,
                GuessNumAwardSku.SKUid == data.get('skuid'),
                GuessNumAwardSku.isdelete == False,
                GuessNumAwardSku.SKUstock > 0).first_('商品库存不足')
            # 时间判断来获取折扣
            if now.hour < 16:
                discount = 0
            elif now.hour == 16 and now.minute < 20:
                discount = 0
            elif not gn:
                discount = 0
            elif gn.createtime.day < now.day:
                discount = 0
            elif gn.SKUid:
                discount = 0
            else:
                correctnum_instance = CorrectNum.query.filter_by(CNdate=now.date()).first_('大盘结果获取中。请稍后')
                correctnum = correctnum_instance.CNnum
                guessnum = gn.GNnum
                correct_count = self._compare_str(correctnum, guessnum)

                discount = self.get_discount(gnas, correct_count)
            # 打完折扣之后的价格
            price = Decimal(str(gnas.SKUprice)) - Decimal(str(discount))
            if price <= 0:
                price = 0.01
            # 用户信息
            user = User.query.filter_by(USid=request.user.id).first_('用户信息丢失')
            # 商品品牌信息
            pbid = gnap.PBid
            product_brand_instance = ProductBrand.query.filter_by(PBid=pbid, isdelete= False).first()
            # 商品分类
            product_category = ProductCategory.query.filter_by(PCid=gnap.PCid, isdelete=False).first()
            # sku详情
            sku_instance = ProductSku.query.filter_by(SKUid=data.get('skuid'), isdelete=False).first()
            # 商品详情
            product_instance = Products.query.filter_by(PRid=gnap.PRid, isdelete=False).first()
            # 地址
            user_address_instance = UserAddress.filter_by(UAid=data.get('uaid'), USid=user.USid).first_('地址信息有误')
            omrecvphone = user_address_instance.UAphone
            areaid = user_address_instance.AAid
            # 地址拼接
            area, city, province = db.session.query(AddressArea, AddressCity, AddressProvince).filter(
                AddressArea.ACid == AddressCity.ACid, AddressCity.APid == AddressProvince.APid).filter(
                AddressArea.AAid == areaid).first_('地址有误')
            address = getattr(province, "APname", '') + getattr(city, "ACname", '') + getattr(
                area, "AAname", '')
            omrecvaddress = address + user_address_instance.UAtext
            omrecvname = user_address_instance.UAname
            # 支付单号
            opayno = self.wx_pay.nonce_str
            # 支付方式
            opaytype = data.get('opaytype')
            # 下单设备
            try:
                omclient = int(data.get('omclient', Client.wechat.value))
                Client(omclient)
            except Exception as e:
                raise ParamsError('客户端或商品来源错误')

            suid = gnaa.SUid if not gnaa.GNAAfrom else None

            # 创建主单
            order_main_instance = OrderMain.create({
                'OMid': omid,
                'OMno': self._generic_omno(),
                'OPayno': opayno,
                'USid': user.USid,
                'OMfrom': OrderFrom.guess_num_award.value,
                'PBname': product_brand_instance.PBname,
                'PBid': pbid,
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
            })
            db.session.add(order_main_instance)
            # 创建副单
            order_part_instance = OrderPart.create({
                'OMid': order_main_instance.OMid,
                'OPid': str(uuid.uuid1()),
                'SKUid': data.get('skuid'),
                'PRattribute': gnap.PRattribute,
                'SKUattriteDetail': gnas.SKUattriteDetail,
                'PRtitle': gnap.PRtitle,
                'SKUsn': sku_instance.SKUsn,
                'PCname': product_category.PCname,
                'SKUprice': price,
                'PRmainpic': product_instance.PRmainpic,
                'OPnum': 1,
                'PRid': product_instance.PRid,
                'OPsubTotal': price,
                # 副单商品来源
                'PRfrom': product_instance.PRfrom,
                'UPperid': user.USsupper1,
                'UPperid2': user.USsupper2,
                'UPperid3': user.USsupper3,
                'USCommission1': user.USCommission1,
                'USCommission2': user.USCommission2,
                'USCommission3': user.USCommission3
                # todo 活动佣金设置
            })
            db.session.add(order_part_instance)
            # 支付数据表
            order_pay_instance = OrderPay.create({
                'OPayid': str(uuid.uuid1()),
                'OPayno': opayno,
                'OPayType': opaytype,
                'OPayMount': price,
            })
            db.session.add(order_pay_instance)
            gn.PRid = gnap.PRid
            gn.SKUid = gnas.SKUid
            gn.Price = price
            gn.GNNAid = gnaa.GNAAid

        from planet.extensions.tasks import auto_cancle_order

        auto_cancle_order.apply_async(args=([omid],), countdown=30 * 60, expires=40 * 60, )
        # 生成支付信息
        body = product_instance.PRtitle
        # user = get_current_user()
        openid = user.USopenid1 or user.USopenid2
        pay_args = self._pay_detail(omclient, opaytype, opayno, float(price), body, openid=openid)
        response = {
            'pay_type': PayType(opaytype).name,
            'opaytype': opaytype,
            'args': pay_args
        }
        return Success('创建订单成功', data=response)

    # @token_required
    def today_gnap(self):
        today = date.today()
        gnaa_list = GuessNumAwardApply.query.filter_by(
            GNAAstarttime=today, GNAAstatus=ApplyStatus.agree.value, isdelete=False).all()
        for gnaa in gnaa_list:
            self._fill_gnaa(gnaa)

        # 上方图
        activity = Activity.query.filter_by_({
            'ACtype': ActivityType.guess_num.value,
            'ACshow': True
        }).first_('活动已结束')
        data = {
            'fresh_man': gnaa_list,
            'actopPic': activity['ACtopPic'],
            'acdesc': activity.ACdesc,
            'acname': activity.ACname,
        }
        return Success('获取今天猜数字活动成功', data=data)

    @token_required
    def get_discount_by_skuid(self):
        data = parameter_required(('skuid', 'gnaaid'))
        user = get_current_user()
        # today = date.today()
        now = datetime.now()
        gn = GuessNum.query.filter_by(USid=request.user.id).order_by(GuessNum.createtime.desc()).first()
        gnas = GuessNumAwardSku.query.filter(
            GuessNumAwardSku.SKUid == data.get('skuid'),
            GuessNumAwardSku.GNAPid == GuessNumAwardProduct.GNAPid,
            GuessNumAwardProduct.GNAAid == data.get('gnaaid'),
            GuessNumAwardSku.isdelete == False,
            GuessNumAwardProduct.isdelete == False,
        )
        print(str(gnas))
        gnas = gnas.first()
        # 时间判断来获取折扣
        if now.hour < 16:
            discount = 0
        elif now.hour == 16 and now.minute < 20:
            discount = 0
        elif not gn:
            discount = 0
        elif gn.createtime.day < now.day:
            discount = 0
        elif gn.SKUid:
            discount = 0
        else:
            correctnum_instance = CorrectNum.query.filter_by(CNdate=now.date()).first_('大盘结果获取中。请稍后')
            correctnum = correctnum_instance.CNnum
            guessnum = gn.GNnum
            correct_count = self._compare_str(correctnum, guessnum)

            discount = self.get_discount(gnas, correct_count)

        return Success(data={'discount': discount})

    def list(self):
        """查看自己的申请列表"""
        if is_supplizer():
            suid = request.user.id
        elif is_admin():
            suid = None
        else:
            raise AuthorityError()
        data = parameter_required()
        gnaastatus = data.get('gnaastatus', 'all')
        if str(gnaastatus) == 'all':
            gnaastatus = None
        else:
            gnaastatus = getattr(ApplyStatus, gnaastatus).value
        starttime, endtime = data.get('starttime', '2019-01-01'), data.get('endtime', '2100-01-01')

        gnaa_list = GuessNumAwardApply.query.filter(
            GuessNumAwardApply.isdelete == False).filter_(
            GuessNumAwardApply.GNAAstatus == gnaastatus,
            GuessNumAwardApply.GNAAstarttime >= starttime,
            GuessNumAwardApply.GNAAstarttime <= endtime,
            GuessNumAwardApply.SUid == suid
        ).order_by(GuessNumAwardApply.GNAAstarttime.desc()).all()
        for gnaa in gnaa_list:
            self._fill_apply(gnaa)
            if gnaa.GNAAfrom == ApplyFrom.supplizer.value:
                sup = Supplizer.query.filter_by(SUid=gnaa.SUid).first()
                name = getattr(sup, 'SUname', '')
            elif gnaa.GNAAfrom == ApplyFrom.platform.value:
                admin = Admin.query.filter_by(ADid=gnaa.SUid).first()
                name = getattr(admin, 'ADname', '')
            else:
                name = ''
            gnaa.fill('authname', name)
            gnaa.fill('createtime', gnaa.createtime)

        # 筛选后重新分页
        page = int(data.get('page_num', 1)) or 1
        count = int(data.get('page_size', 15)) or 15
        total_count = len(gnaa_list)
        if page < 1:
            page = 1
        total_page = int(total_count / int(count)) or 1
        start = (page - 1) * count
        if start > total_count:
            start = 0
        if total_count / (page * count) < 0:
            ad_return_list = gnaa_list[start:]
        else:
            ad_return_list = gnaa_list[start: (page * count)]
        request.page_all = total_page
        request.mount = total_count
        return Success(data=ad_return_list)

    def apply_award(self):
        """申请添加奖品"""
        if not (is_supplizer() or is_admin()):
            raise AuthorityError()
        data = parameter_required(('prid', 'prprice', 'skus', 'gnaastarttime'))
        gnaafrom = ApplyFrom.supplizer.value if is_supplizer() else ApplyFrom.platform.value
        # 欲申请商品
        product = Products.query.filter_by(
            PRid=data.get('prid'), isdelete=False, PRstatus=ProductStatus.usual.value).first_('商品未上架')
        product_brand = ProductBrand.query.filter_by(PBid=product.PBid).first_('商品信息不全')
        # 时间列表
        time_list = data.get('gnaastarttime')
        # 申请的sku list
        skus = data.get('skus')
        with db.auto_commit():
            # 系统实际生成的申请id列表， 按日期不同生成不同的申请单
            gnaaid_list = list()
            for day in time_list:
                # 校验是否存在已提交申请
                exist_apply = GuessNumAwardApply.query.filter(
                    GuessNumAwardProduct.PRid == data.get('prid'),
                    # GuessNumAwardProduct.GNAPid == GuessNumAwardApply.GNAPid,
                    GuessNumAwardApply.isdelete == False,
                    GuessNumAwardApply.SUid == request.user.id,
                    GuessNumAwardApply.GNAAstarttime == day).first()
                if exist_apply:
                    raise ParamsError('您已添加过{}日的申请'.format(day))
                # 申请单
                gnaa = GuessNumAwardApply.create({
                    'GNAAid': str(uuid.uuid1()),
                    'SUid': request.user.id,
                    # 'GNAPid': data.get('prid'),
                    'GNAAstarttime': day,
                    'GNAAendtime': day,
                    'GNAAfrom': gnaafrom,
                    'GNAAstatus': ApplyStatus.wait_check.value,
                })
                db.session.add(gnaa)
                gnaaid_list.append(gnaa.GNAAid)
                # 活动商品
                gnap = GuessNumAwardProduct.create({
                    'GNAPid': str(uuid.uuid1()),
                    'GNAAid': gnaa.GNAAid,
                    'PRid': product.PRid,
                    'PRmainpic': product.PRmainpic,
                    'PRtitle': product.PRtitle,
                    'PBid': product.PBid,
                    'PBname': product_brand.PBname,
                    'PRattribute': product.PRattribute,
                    'PRdescription': product.PRdescription,
                    'PRprice': data.get('prprice')
                })
                db.session.add(gnap)
                # 活动sku
                for sku in skus:
                    skuid = sku.get('skuid')
                    skuprice = sku.get('skuprice')
                    skustock = sku.get('skustock')
                    skudiscountone = sku.get('skudiscountone')
                    skudiscounttwo = sku.get('skudiscounttwo')
                    skudiscountthree = sku.get('skudiscountthree')
                    skudiscountfour = sku.get('skudiscountfour')
                    skudiscountfive = sku.get('skudiscountfive')
                    skudiscountsix = sku.get('skudiscountsix')
                    sku_instance = ProductSku.query.filter_by(
                        isdelete=False, PRid=product.PRid, SKUid=skuid).first_('商品sku信息不存在')
                    self._update_stock(-int(skustock), product, sku_instance)
                    # db.session.add(sku)
                    gnas = GuessNumAwardSku.create({
                        'GNASid': str(uuid.uuid1()),
                        'GNAPid': gnap.GNAPid,
                        'SKUid': skuid,
                        'SKUprice': skuprice,
                        'SKUstock': skustock,
                        'SKUdiscountone': skudiscountone,
                        'SKUdiscounttwo': skudiscounttwo,
                        'SKUdiscountthree': skudiscountthree,
                        'SKUdiscountfour': skudiscountfour,
                        'SKUdiscountfive': skudiscountfive,
                        'SKUdiscountsix': skudiscountsix,
                    })
                    db.session.add(gnas)

        # 添加到审批流
        for gnaaid in gnaaid_list:
            super(CGuessNum, self).create_approval('toguessnum', request.user.id, gnaaid, gnaafrom)
        return Success('申请添加成功', {'gnaaid': gnaaid_list})

    def update_apply(self):
        """修改猜数字奖品申请, 一次只能处理一天的一个商品"""
        if not (is_supplizer() or is_admin()):
            raise AuthorityError()
        # data = parameter_required(('gnaaid', 'skuprice', 'skustock'))
        data = parameter_required(('gnaaid', 'prid', 'prprice', 'skus'))
        with db.auto_commit():
            # 获取申请单
            apply_info = GuessNumAwardApply.query.filter(GuessNumAwardApply.GNAAid == data.get('gnaaid'),
                                                         GuessNumAwardApply.GNAAstatus.in_([ApplyStatus.reject.value,
                                                                                           ApplyStatus.cancle.value])
                                                         ).first_('只有已拒绝或撤销状态的申请可以进行修改')
            if apply_info.SUid != request.user.id:
                raise AuthorityError('仅可修改自己提交的申请')
            gnaafrom = ApplyFrom.supplizer.value if is_supplizer() else ApplyFrom.platform.value
            # 解除和原商品属性的绑定
            GuessNumAwardProduct.query.filter_by(GNAAid=apply_info.GNAAid, isdelete=False).delete_()
            # product_old.isdelete = True

            # 如果没有修改时间，则用之前时间
            gnaastarttime = data.get('gnaastarttime') or apply_info.GNAAstarttime
            # 如果修改了时间，检测是否有冲突
            exist_apply_list = list()

            # 重新添加商品属性
            skus = data.get('skus')
            product = Products.query.filter_by(
                PRid=data.get('prid'), isdelete=False, PRstatus=ProductStatus.usual.value).first_('商品未上架')
            product_brand = ProductBrand.query.filter_by(PBid=product.PBid).first_('商品信息不全')
            # 新的商品属性
            gnap = GuessNumAwardProduct.create({
                'GNAPid': str(uuid.uuid1()),
                'GNAAid': apply_info.GNAAid,
                'PRid': product.PRid,
                'PRmainpic': product.PRmainpic,
                'PRtitle': product.PRtitle,
                'PBid': product.PBid,
                'PBname': product_brand.PBname,
                'PRattribute': product.PRattribute,
                'PRdescription': product.PRdescription,
                'PRprice': data.get('prprice')
            })
            db.session.add(gnap)
            # 新的sku属性
            for sku in skus:
                # 冲突校验。 如果冲突，则跳过，并予以提示
                exits_apply = GuessNumAwardApply.query.filter(
                    GuessNumAwardApply.GNAAid != apply_info.GNAAid,
                    GuessNumAwardApply.GNAAstarttime == gnaastarttime,
                    GuessNumAwardProduct.GNAAid == GuessNumAwardApply.GNAAid,
                    GuessNumAwardProduct.PRid == data.get('prid'),
                    GuessNumAwardSku.SKUid == sku.get('skuid'),
                    GuessNumAwardSku.GNAPid == GuessNumAwardProduct.GNAPid,
                    GuessNumAwardProduct.isdelete == False,
                    GuessNumAwardSku.isdelete == False,
                    GuessNumAwardApply.isdelete == False
                ).first()

                skuid = sku.get('skuid')
                skuprice = sku.get('skuprice')
                skustock = sku.get('skustock')
                SKUdiscountone = sku.get('skudiscountone')
                SKUdiscounttwo = sku.get('skudiscounttwo')
                SKUdiscountthree = sku.get('skudiscountthree')
                SKUdiscountfour = sku.get('skudiscountfour')
                SKUdiscountfive = sku.get('skudiscountfive')
                SKUdiscountsix = sku.get('skudiscountsix')
                sku_instance = ProductSku.query.filter_by(
                    isdelete=False, PRid=product.PRid, SKUid=skuid).first_('商品sku信息不存在')

                if exits_apply:
                    exist_apply_list.append(sku_instance)
                    continue
                # 库存处理
                self._update_stock(-int(skustock), product, sku_instance)

                gnas = GuessNumAwardSku.create({
                    'GNASid': str(uuid.uuid1()),
                    'GNAPid': gnap.GNAPid,
                    'SKUid': skuid,
                    'SKUprice': skuprice,
                    'SKUstock': skustock,
                    'SKUdiscountone': SKUdiscountone,
                    'SKUdiscounttwo': SKUdiscounttwo,
                    'SKUdiscountthree': SKUdiscountthree,
                    'SKUdiscountfour': SKUdiscountfour,
                    'SKUdiscountfive': SKUdiscountfive,
                    'SKUdiscountsix': SKUdiscountsix,
                })
                db.session.add(gnas)
                apply_info.GNAAstatus = ApplyStatus.wait_check.value
        super(CGuessNum, self).create_approval('toguessnum', request.user.id, apply_info.GNAAid, gnaafrom)

        return Success('修改成功', {'gnaaid': apply_info.GNAAid, 'skus': exist_apply_list})

    def award_detail(self):
        """查看申请详情"""
        # todo 字段修改
        if not (is_supplizer() or is_admin()):
            args = parameter_required(('gnaaid',))
            gnaaid = args.get('gnaaid')
            award = GuessNumAwardApply.query.filter_by_(GNAAid=gnaaid).first_('该申请已被删除')
            self._fill_apply(award)
            return Success('获取成功', award)

    def shelf_award(self):
        """撤销申请"""
        if not (is_supplizer() or is_admin()):
            raise AuthorityError()
        data = parameter_required(('gnaaid',))
        gnaaid = data.get('gnaaid')
        with db.auto_commit():
            apply_info = GuessNumAwardApply.query.filter_by_(GNAAid=gnaaid).first_('无此申请记录')

            if apply_info.GNAAstatus != ApplyStatus.wait_check.value:
                raise StatusError('只有在审核状态的申请可以撤销')
            if apply_info.SUid != request.user.id:
                raise AuthorityError('仅可撤销自己提交的申请')
            apply_info.GNAAstatus = ApplyStatus.cancle.value

            # 获取原商品属性
            gnap_old = GuessNumAwardProduct.query.filter(GuessNumAwardProduct.GNAAid == apply_info.GNAAid,
                                                            GuessNumAwardProduct.isdelete == False).first()
            product = Products.query.filter_by(PRid=gnap_old.PRid, isdelete=False).first_('商品信息出错')
            # 获取原sku属性
            gnas_old = GuessNumAwardSku.query.filter(
                apply_info.GNAAid == GuessNumAwardProduct.GNAAid,
                GuessNumAwardSku.GNAPid == GuessNumAwardProduct.GNAPid,
                GuessNumAwardSku.isdelete == False,
                GuessNumAwardProduct.isdelete == False,
            ).all()

            # 遍历原sku 将库存退出去
            for sku in gnas_old:
                sku_instance = ProductSku.query.filter_by(
                    isdelete=False, PRid=product.PRid, SKUid=sku.SKUid).first_('商品sku信息不存在')
                self._update_stock(int(sku.SKUstock), product, sku_instance)

            # 同时将正在进行的审批流改为取消
            approval_info = Approval.query.filter_by_(AVcontent=gnaaid, AVstartid=request.user.id,
                                                      AVstatus=ApplyStatus.wait_check.value).first()
            approval_info.AVstatus = ApplyStatus.cancle.value
        return Success('取消成功', {'gnaaid': gnaaid})

    def delete_apply(self):
        """删除申请"""
        if is_supplizer():
            usid = request.user.id
            sup = Supplizer.query.filter_by_(SUid=usid).first_('供应商信息错误')
            current_app.logger.info('Supplizer {} delete guessnum apply'.format(sup.SUname))
        elif is_admin():
            usid = request.user.id
            admin = Admin.query.filter_by_(ADid=usid).first_('管理员信息错误')
            current_app.logger.info('Admin {} guessnum apply'.format(admin.ADname))
            sup = None
        else:
            raise AuthorityError()
        data = parameter_required(('gnaaid',))
        gnaaid = data.get('gnaaid')
        with db.auto_commit():
            apply_info = GuessNumAwardApply.query.filter_by_(GNAAid=gnaaid).first_('无此申请记录')
            if sup:
                assert apply_info.SUid == usid, '供应商只能删除自己提交的申请'
            if apply_info.GNAAstatus not in [ApplyStatus.cancle.value, ApplyStatus.reject.value, ApplyStatus.shelves.value]:
                raise StatusError('只能删除已拒绝或已撤销状态下的申请')
            apply_info.isdelete = True
        return Success('删除成功', {'gnaaid': gnaaid})

    def shelves(self):
        """下架申请"""
        if is_supplizer():
            usid = request.user.id
            sup = Supplizer.query.filter_by_(SUid=usid).first_('供应商信息错误')
            current_app.logger.info('Supplizer {} delete guessnum apply'.format(sup.SUname))
        elif is_admin():
            usid = request.user.id
            admin = Admin.query.filter_by_(ADid=usid).first_('管理员信息错误')
            current_app.logger.info('Admin {} guessnum apply'.format(admin.ADname))
            sup = None
        else:
            raise AuthorityError()
        data = parameter_required(('gnaaid',))
        gnaaid = data.get('gnaaid')
        with db.auto_commit():
            apply_info = GuessNumAwardApply.query.filter_by_(GNAAid=gnaaid).first_('无此申请记录')
            if sup:
                assert apply_info.SUid == usid, '供应商只能下架自己的申请'
            if apply_info.GNAAstatus != ApplyStatus.agree.value:
                raise StatusError('只能下架已通过的申请')
            apply_info.GNAAstatus = ApplyStatus.shelves.value
        return Success('下架成功', {'mbaid': gnaaid})

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

    def _fill_apply(self, award):
        award.fill('gnaastatus_zh', ApplyStatus(award.GNAAstatus).zh_value)
        product = GuessNumAwardProduct.query.filter_by(GNAAid=award.GNAAid, isdelete=False).first()
        # product = Products.query.filter_by_(PRid=gnap.PRid).first_('商品已下架')
        product.PRattribute = json.loads(product.PRattribute)
        # product.PRremarks = json.loads(getattr(product, 'PRremarks') or '{}')
        # 顶部图
        images = ProductImage.query.filter_by_(PRid=product.PRid).order_by(ProductImage.PIsort).all()
        product.fill('images', images)
        # 品牌
        brand = ProductBrand.query.filter_by_(PBid=product.PBid).first() or {}
        product.fill('brand', brand)
        gnas_list = GuessNumAwardSku.query.filter_by(GNAPid=product.GNAPid, isdelete=False).all()
        for gnas in gnas_list:
            sku = ProductSku.query.filter_by_(SKUid=gnas.SKUid).first_('没有该skuid信息')
            gnas.fill('SKUattriteDetail', json.loads(sku.SKUattriteDetail))
            gnas.fill('SKUpic', sku.SKUpic)
            gnas.fill('SKUsn', sku.SKUsn)
            gnas.fill('SkudevideRate', sku.SkudevideRate)

        product.fill('sku', gnas_list)

        award.fill('product', product)

    def _compare_str(self, str_a, str_b):
        sum_ = 0
        str_a_list = str_a.split('.')
        str_b_list = str_b.split('.')

        str_a_pre = str_a_list[0]
        str_b_pre = str_b_list[0][-len(str_a_pre):]
        while len(str_b_pre) < len(str_a_pre):
            str_b_pre = 'a' + str_b_pre

        for index, str_char in enumerate(str_a_pre):
            if index >= len(str_b_pre): break

            if str_char == str_b_pre[index]: sum_ += 1
        if len(str_b_list) > 1:
            str_a_behind = str_a_list[1]
            str_b_behind = str_b_list[1][:len(str_a_behind)]
            while len(str_b_behind) < len(str_a_behind):
                str_b_behind = str_b_behind + 'a'

            for index, str_char in enumerate(str_a_behind):
                if index >= len(str_b_behind): break

                if str_char == str_b_behind[index]: sum_ += 1

        return sum_

    def get_discount(self, gnas, num):
        if num == 0:
            return 0
        if num == 1:
            return gnas.SKUdiscountone
        if num == 2:
            return gnas.SKUdiscounttwo
        if num == 3:
            return gnas.SKUdiscountthree
        if num == 4:
            return gnas.SKUdiscountfour
        if num == 5:
            return gnas.SKUdiscountfive
        if num == 6:
            return gnas.SKUdiscountsix
        return 0

    def _fill_gnaa(self, gnaa):
        gnap = GuessNumAwardProduct.query.filter_by(GNAAid=gnaa.GNAAid, isdelete=False).first()
        if not gnap:
            current_app.logger.info('该申请无商品 gnaaid = {0}'.format(gnaa.GNAAid))
            return
        product = Products.query.filter_by(PRid=gnap.PRid, isdelete=False).first()
        if not product:
            current_app.logger.info('该商品已删除 prid = {0}'.format(gnap.PRid))
            return

        if isinstance(product.PRattribute, str):
            product.PRattribute = json.loads(product.PRattribute)
        if isinstance(getattr(product, 'PRremarks', None) or '{}', str):
            product.PRremarks = json.loads(getattr(product, 'PRremarks', None) or '{}')

        pb = ProductBrand.query.filter_by_(PBid=product.PBid).first()

        images = ProductImage.query.filter(
            ProductImage.PRid == product.PRid, ProductImage.isdelete == False).order_by(
            ProductImage.PIsort).all()
        product.fill('images', images)
        product.fill('brand', pb)
        gnas_list = GuessNumAwardSku.query.filter_by(GNAPid=gnap.GNAPid, isdelete=False).all()
        skus = list()
        sku_value_item = list()
        for gnas in gnas_list:
            sku = ProductSku.query.filter_by(SKUid=gnas.SKUid, isdelete=False).first()
            if not sku:
                current_app.logger.info('该sku已删除 skuid = {0}'.format(gnas.SKUid))
                continue
            sku.hide('SKUprice')
            sku.hide('SKUstock')
            sku.fill('skuprice', gnas.SKUprice)
            sku.fill('skustock', gnas.SKUstock)
            sku.fill('SKUdiscountone', gnas.SKUdiscountone)
            sku.fill('SKUdiscounttwo', gnas.SKUdiscounttwo)
            sku.fill('SKUdiscountthree', gnas.SKUdiscountthree)
            sku.fill('SKUdiscountfour', gnas.SKUdiscountfour)
            sku.fill('SKUdiscountfive', gnas.SKUdiscountfive)
            sku.fill('SKUdiscountsix', gnas.SKUdiscountsix)
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
        gnaa.fill('product', product)
