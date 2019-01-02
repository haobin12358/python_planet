# -*- coding: utf-8 -*-
import json
import uuid
from datetime import datetime, date, timedelta

from flask import request
from sqlalchemy import cast, Date, extract

from planet.common.error_response import StatusError, ParamsError, NotFound, AuthorityError
from planet.common.params_validates import parameter_required
from planet.common.success_response import Success
from planet.common.token_handler import token_required, get_current_user, is_supplizer, is_admin
from planet.control.BaseControl import BASEAPPROVAL
from planet.extensions.register_ext import db
from planet.extensions.validates.activty import GuessNumCreateForm, GuessNumGetForm, GuessNumHistoryForm
from planet.models import GuessNum, CorrectNum, ProductSku, ProductItems, GuessAwardFlow, Products, ProductBrand, \
    UserAddress, AddressArea, AddressCity, AddressProvince, OrderMain, OrderPart, OrderPay, GuessNumAwardApply, \
    ProductSkuValue, ProductImage, Approval, Supplizer, Admin
from planet.config.enums import ActivityRecvStatus, OrderFrom, Client, PayType, ProductStatus, GuessNumAwardStatus, \
    ApprovalType, ApplyStatus, ApplyFrom
from planet.extensions.register_ext import alipay, wx_pay
from .COrder import COrder


class CGuessNum(COrder, BASEAPPROVAL):

    @token_required
    def creat(self):
        """参与活动"""
        date_now = datetime.now()
        if date_now.hour > 15:
            raise StatusError('15点以后不开放')
        if date_now.weekday() in [0, 6]:
            raise StatusError('周六周日不开放')
        form = GuessNumCreateForm().valid_data()
        gnnum = form.gnnum.data
        usid = request.user.id

        # if date_now.hour > 15:  # 15点以后参与次日的
        #     gndate = date.today() + timedelta(days=1)
        # else:
        #     gndate = date.today()

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
                'USid': usid,
                'PRid': today_raward.PRid,
                'SKUid': today_raward.SKUid,
                'Price': today_raward.SKUprice,
                # 'GNdate': gndate
            })
            db.session.add(guess_instance)
        return Success('参与成功')

    @token_required
    def get(self):
        """获得单日个人参与"""
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

            product = Products.query.filter_by_({'PRid': join_history.PRid}).first()
            product.fields = ['PRid', 'PRmainpic', 'PRtitle']
            join_history.fill('product', product)
        return Success(data=join_history)

    @token_required
    def history_join(self):
        """获取历史参与记录"""
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

            product = Products.query.filter_by_({'PRid': join_history.PRid}).first()
            product.fields = ['PRid', 'PRmainpic', 'PRtitle']
            join_history.fill('product', product)
        return Success(data=join_historys).get_body(correct_count=correct_count)

    @token_required
    def recv_award(self):
        data = parameter_required(('gnid', 'skuid', 'omclient', 'uaid', 'opaytype'))
        gnid = data.get('gnid')
        skuid = data.get('skuid')
        usid = request.user.id
        uaid = data.get('uaid')
        opaytype = data.get('opaytype')
        try:
            omclient = int(data.get('omclient', Client.wechat.value))  # 下单设备
            Client(omclient)
        except Exception as e:
            raise ParamsError('客户端或商品来源错误')

        with db.auto_commit():
            s_list = []
            # 参与记录
            guess_num = GuessNum.query.filter_by_().filter_by_({
                'SKUid': skuid,
                'USid': usid,
                'GNid': gnid
            }).first_('未参与')
            price = guess_num.Price

            # 领奖流水
            guess_award_flow_instance = GuessAwardFlow.query.filter_by_({
                'GNid': gnid,
                'GAFstatus': ActivityRecvStatus.wait_recv.value,
            }).first_('未中奖或已领奖')
            sku_instance = ProductSku.query.filter_by_({"SKUid": skuid}).first_('sku: {}不存在'.format(skuid))
            product_instance = Products.query.filter_by_({"PRid": sku_instance.PRid}).first_('商品已下架')
            pbid = product_instance.PBid
            product_brand_instance = ProductBrand.query.filter_by({'PBid': pbid}).first_()
            # 领奖状态改变
            guess_award_flow_instance.GAFstatus = ActivityRecvStatus.ready_recv.value
            s_list.append(guess_award_flow_instance)
            # 用户的地址信息
            user_address_instance = UserAddress.query.filter_by_({'UAid': uaid, 'USid': usid}).first_('地址信息不存在')
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

            # 创建订单
            omid = str(uuid.uuid1())
            opayno = self.wx_pay.nonce_str
            # 主单
            order_main_dict = {
                'OMid': omid,
                'OMno': self._generic_omno(),
                'OPayno': opayno,
                'USid': usid,
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
            }
            order_main_instance = OrderMain.create(order_main_dict)
            s_list.append(order_main_instance)
            user = get_current_user()
            order_part_dict = {
                'OMid': omid,
                'OPid': str(uuid.uuid1()),
                'SKUid': skuid,
                'PRattribute': product_instance.PRattribute,
                'SKUattriteDetail': sku_instance.SKUattriteDetail,
                'PRtitle': product_instance.PRtitle,
                'SKUprice': sku_instance.SKUprice,
                'PRmainpic': product_instance.PRmainpic,
                'OPnum': 1,
                'PRid': product_instance.PRid,
                'OPsubTotal': price,
                # 副单商品来源
                'PRfrom': product_instance.PRfrom,
                'PRcreateId': product_instance.CreaterId,
                'UPperid': user.USsupper1,
                'UPperid2': user.USsupper2,
                # todo 活动佣金设置
            }
            order_part_instance = OrderPart.create(order_part_dict)
            s_list.append(order_part_instance)
            # 支付数据表
            order_pay_dict = {
                'OPayid': str(uuid.uuid1()),
                'OPayno': opayno,
                'OPayType': opaytype,
                'OPayMount': price,
            }
            order_pay_instance = OrderPay.create(order_pay_dict)
            s_list.append(order_pay_instance)
            db.session.add_all(s_list)


            # todo sku库存变化 取中奖日期匹配 当前通过的申请确定skuid

        # 生成支付信息
        body = product_instance.PRtitle
        user = get_current_user()
        openid = user.USopenid1 or user.USopenid2
        pay_args = self._pay_detail(omclient, opaytype, opayno, float(price), body, openid=openid)
        response = {
            'pay_type': PayType(opaytype).name,
            'opaytype': opaytype,
            'args': pay_args
        }
        return Success('创建订单成功', data=response)

    def list(self):
        """查看自己的申请列表"""
        if is_supplizer():
            suid = request.user.id
        elif is_admin():
            suid = None
        else:
            raise AuthorityError()
        award_list = GuessNumAwardApply.query.filter_by_(SUid=suid).all_with_page()
        for award in award_list:
            sku = ProductSku.query.filter_by_(SKUid=award.SKUid).first()
            award.fill('skupic', sku['SKUpic'])
            product = Products.query.filter_by_(PRid=award.PRid).first()
            award.fill('prtitle', product.PRtitle)
            award.fill('prmainpic', product['PRmainpic'])
            brand = ProductBrand.query.filter_by_(PBid=product.PBid).first()
            award.fill('pbname', brand.PBname)
            award.fill('gnaastatus_zh', ApplyStatus(award.GNAAstatus).zh_value)
            if award.GNAAfrom == ApplyFrom.supplizer.value:
                sup = Supplizer.query.filter_by_(SUid=award.SUid).first()
                name = getattr(sup, 'SUname', '')
            elif award.GNAAfrom == ApplyFrom.platform.value:
                admin = Admin.query.filter_by_(ADid=award.SUid).first()
                name = getattr(admin, 'ADname', '')
            else:
                name = ''
            award.fill('authname', name)
        return Success(data=award_list)

    def apply_award(self):
        """申请添加奖品"""
        if not (is_supplizer() or is_admin()):
            raise AuthorityError()
        data = parameter_required(('skuid', 'prid', 'gnaastarttime', 'skuprice'))
        skuid, prid, skustock = data.get('skuid'), data.get('prid'), data.get('skustock', 1)
        gnaafrom = ApplyFrom.supplizer.value if is_supplizer() else ApplyFrom.platform.value
        sku = ProductSku.query.filter_by_(SKUid=skuid).first_('没有该skuid信息')
        Products.query.filter(Products.PRid == prid, Products.isdelete == False,
                              Products.PRstatus == ProductStatus.usual.value
                              ).first_('当前商品状态不允许进行申请')
        assert sku.PRid == prid, 'sku与商品信息不对应'

        time_list = data.get('gnaastarttime')
        if not isinstance(time_list, list):
            raise ParamsError('参数 gnaastarttime 格式错误')

        # 将申请事物时间分割成每天单位
        # begin_time = str(data.get('gnaastarttime'))[:10]
        # end_time = str(data.get('gnaaendtime'))[:10]
        # time_list = self._getBetweenDay(begin_time, end_time)

        award_instance_list = list()
        gnaaid_list = list()
        with db.auto_commit():
            for day in time_list:
                # 先检测是否存在相同skuid，相同日期的申请
                exist_apply_sku = GuessNumAwardApply.query.filter(GuessNumAwardApply.SKUid == skuid,
                                                                  GuessNumAwardApply.isdelete == False,
                                                                  GuessNumAwardApply.SUid == request.user.id,
                                                                  GuessNumAwardApply.GNAAstarttime == day).first()
                if exist_apply_sku:
                    raise ParamsError('您已添加过{}日的申请'.format(day))
                award_dict = {
                    'GNAAid': str(uuid.uuid1()),
                    'SUid': request.user.id,
                    'SKUid': skuid,
                    'PRid': prid,
                    'GNAAstarttime': day,
                    'GNAAendtime': day,
                    'SKUprice': float(data.get('skuprice', 0.01)),
                    'SKUstock': int(skustock),
                    'GNAAstatus': ApplyStatus.wait_check.value,
                    'GNAAfrom': gnaafrom,
                }
                award_instance = GuessNumAwardApply.create(award_dict)
                gnaaid_list.append(award_dict['GNAAid'])
                award_instance_list.append(award_instance)
                # 添加到审批流
                super().create_approval('toguessnum', request.user.id, award_dict['GNAAid'], gnaafrom)
            db.session.add_all(award_instance_list)
        return Success('申请添加成功', {'gnaaid': gnaaid_list})

    def update_apply(self):
        """修改猜数字奖品申请"""
        if not (is_supplizer() or is_admin()):
            raise AuthorityError()
        data = parameter_required(('gnaaid', 'skuprice', 'skustock'))
        gnaaid, skuid, prid, skustock = data.get('gnaaid'), data.get('skuid'), data.get('prid'), data.get('skustock')
        apply_info = GuessNumAwardApply.query.filter(GuessNumAwardApply.GNAAid == gnaaid,
                                                     GuessNumAwardApply.GNAAstatus.in_([ApplyStatus.reject.value,
                                                                                       ApplyStatus.cancle.value])
                                                     ).first_('只有下架或撤销状态的申请可以进行修改')
        if apply_info.SUid != request.user.id:
            raise AuthorityError('仅可修改自己提交的申请')
        gnaafrom = ApplyFrom.supplizer.value if is_supplizer() else ApplyFrom.platform.value
        sku = ProductSku.query.filter_by_(SKUid=skuid).first_('没有该skuid信息')
        Products.query.filter(Products.PRid == prid, Products.isdelete == False,
                              Products.PRstatus == ProductStatus.usual.value
                              ).first_('仅可将上架中的商品用于申请')  # 当前商品状态不允许进行申请

        assert sku.PRid == prid, 'sku与商品信息不对应'
        with db.auto_commit():
            award_dict = {
                'SKUid': skuid,
                'PRid': prid,
                'GNAAstarttime': data.get('gnaastarttime'),
                'GNAAendtime': data.get('gnaastarttime'),
                'SKUprice': float(data.get('skuprice', 0.01)),
                'SKUstock': int(skustock),
                'GNAAstatus': ApplyStatus.wait_check.value,
                'GNAAfrom': gnaafrom,
            }
            award_dict = {k: v for k, v in award_dict.items() if v is not None}
            GuessNumAwardApply.query.filter_by_(GNAAid=gnaaid).update(award_dict)
        super().create_approval('toguessnum', request.user.id, gnaaid, gnaafrom)

        return Success('修改成功', {'gnaaid': gnaaid})

    def award_detail(self):
        """查看申请详情"""
        if not (is_supplizer() or is_admin()):
            args = parameter_required(('gnaaid',))
            gnaaid = args.get('gnaaid')
            award = GuessNumAwardApply.query.filter_by_(GNAAid=gnaaid).first_('该申请已被删除')
            product = Products.query.filter_by_(PRid=award.PRid).first_('商品已下架')
            product.PRattribute = json.loads(product.PRattribute)
            product.PRremarks = json.loads(getattr(product, 'PRremarks') or '{}')
            # 顶部图
            images = ProductImage.query.filter_by_(PRid=product.PRid).order_by(ProductImage.PIsort).all()
            product.fill('images', images)
            # 品牌
            brand = ProductBrand.query.filter_by_(PBid=product.PBid).first() or {}
            product.fill('brand', brand)
            sku = ProductSku.query.filter_by_(SKUid=award.SKUid).first_('没有该skuid信息')
            sku.SKUattriteDetail = json.loads(sku.SKUattriteDetail)
            if sku.SKUstock:
                sku.hide('SKUstock')
            product.fill('sku', sku)
            # # sku value
            # 是否有skuvalue, 如果没有则自行组装
            sku_value_item_reverse = []
            for index, name in enumerate(product.PRattribute):
                value = sku.SKUattriteDetail[index]
                temp = {
                    'name': name,
                    'value': value
                }
                sku_value_item_reverse.append(temp)
            product.fill('skuvalue', sku_value_item_reverse)
            award.fill('product', product)
            return Success('获取成功', award)

    def shelf_award(self):
        """撤销申请"""
        if not (is_supplizer() or is_admin()):
            raise AuthorityError()
        data = parameter_required(('gnaaid',))
        gnaaid = data.get('gnaaid')
        apply_info = GuessNumAwardApply.query.filter_by_(GNAAid=gnaaid).first_('无此申请记录')
        if apply_info.MBAstatus != ApplyStatus.wait_check.value:
            raise StatusError('只有在审核状态的申请可以撤销')
        if apply_info.SUid != request.user.id:
            raise AuthorityError('仅可撤销自己提交的申请')
        apply_info.GNAAstatus = ApplyStatus.cancle.value
        # 同时将正在进行的审批流改为取消
        approval_info = Approval.query.filter_by_(AVcontent=gnaaid, AVstartid=request.user.id,
                                                  AVstatus=ApplyStatus.wait_check.value).first()
        approval_info.AVstatus = ApplyStatus.cancle.value
        db.session.commit()
        return Success('取消成功', {'gnaaid': gnaaid})

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