import random
import uuid
from datetime import date
from decimal import Decimal

from flask import current_app
from sqlalchemy.dialects.postgresql import json

from planet.common.error_response import StatusError, DumpliError, NotFound
from planet.common.success_response import Success
from planet.common.token_handler import token_required, get_current_user
from planet.config.enums import ApplyStatus, ActivityType, ActivityRecvStatus, OrderFrom, PayType
from planet.extensions.register_ext import db, wx_pay
from planet.extensions.validates.activty import MagicBoxOpenForm, ParamsError, MagicBoxJoinForm, request, \
    MagicBoxRecvAwardForm
from planet.models import MagicBoxJoin, MagicBoxApply, GuessNumAwardApply, MagicBoxOpen, User, Activity, ProductBrand, \
    AddressArea, UserAddress, AddressCity, AddressProvince, OrderMain, Products, OrderPart, ProductSku, OrderPay
from .CUser import CUser
from .COrder import COrder


class CMagicBox(CUser, COrder):

    @token_required
    def open(self):
        """好友帮拆"""
        # 判断帮拆活动总控制是否结束
        Activity.query.filter_by({
            'ACtype': ActivityType.magic_box.value
        }).first_('活动已结束')

        form = MagicBoxOpenForm().valid_data()
        mbjid = form.mbjid.data
        level = form.level.data
        levle_attr = dict(form.level.choices).get(level)
        usid = request.user.id
        # 源参与记录
        magic_box_join = MagicBoxJoin.query.filter_by({'MBJid': mbjid}).first_('请点击好友发来邀请链接')
        if magic_box_join.MBJstatus != ActivityRecvStatus.wait_recv.value:
            raise StatusError('已领奖或已过期')
        if magic_box_join.USid == request.user.id:
            raise NotFound('仅可打开好友分享的魔盒')
        mbaid = magic_box_join.MBAid
        # 活动是否在进行
        magic_box_apply = MagicBoxApply.query.filter_by_().filter(
            MagicBoxApply.MBAid == mbaid,
            MagicBoxApply.MBAstatus == ApplyStatus.agree.value
        ).first_('活动不存在')
        today = date.today()
        lasting = magic_box_apply.AgreeEndtime >= today
        if not lasting:
            raise StatusError('活动过期')
        with db.auto_commit():
            # 是否已经帮开奖
            ready_open = MagicBoxOpen.query.filter_by_({'USid': usid,
                                                        'MBJid': mbjid}).first()
            if ready_open:
                raise DumpliError('已经帮好友拆过')

            # 价格变动随机
            current_level_str = getattr(magic_box_apply, levle_attr)
            current_level_json = json.loads(current_level_str)  # 列表 ["1-2", "3-4"]

            current_level_json[0] = list(map(lambda x: int(x) * -1, current_level_json[0].split('-')))  # 第0个元素是-
            if len(current_level_json) == 2:
                current_level_json[1] = list(map(int, current_level_json[1].split('-')))  # 第1个元素是+
            random_choice_first = random.choice(current_level_json)  # 选择是- 还是+
            final_reduce = random.uniform(*random_choice_first)  # 最终价格变动
            final_reduce = round(Decimal(final_reduce), 2)
            # 价格计算
            final_price = Decimal(magic_box_join.MBJcurrentPrice) + final_reduce
            if final_price > magic_box_apply.SKUprice:
                final_price = magic_box_apply.SKUprice
            if final_price < magic_box_apply.SKUminPrice:
                final_price = magic_box_apply.SKUminPrice
            final_price = round(final_price, 2)
            # 帮拆记录
            user = User.query.filter_by_({'USid': usid}).first()
            mb_open = MagicBoxOpen.create({
                'MBOid': str(uuid.uuid1()),
                'USid': usid,
                'MBJid': mbjid,
                'MBOgear': int(level),
                'MBOresult': float(final_reduce),
                'MBOprice': float(final_price),
                'USname': user.USname
            })
            # 源参与价格修改
            magic_box_join.MBJcurrentPrice = float(final_price)
            db.session.add(mb_open)
        return Success(data={
            'final_reduce': float(final_reduce),
            'final_price': float(final_price)
        })

    @token_required
    def join(self):
        """参与活动, 分享前(或分享后调用), 创建用户的参与记录
        """
        # 判断帮拆活动总控制是否结束
        Activity.query.filter_by({
            'ACtype': ActivityType.magic_box.value
        }).first_('活动已结束')
        form = MagicBoxJoinForm().valid_data()
        mbaid = form.mbaid.data
        usid = request.user.id
        with db.auto_commit():
            today = date.today()
            magic_box_apply = MagicBoxApply.query.filter_by_().filter(
                MagicBoxApply.AgreeStartime <= today,
                MagicBoxApply.AgreeEndtime >= today,
                MagicBoxApply.MBAid == mbaid
            ).first_('活动结束')
            # 已参与则不再新建记录
            magic_box_join = MagicBoxJoin.query.filter_by_({
                'USid': usid,
                'MBAid': mbaid
            }).first()
            if not magic_box_join:
                # 一期活动只可参与一次
                magic_box_join = MagicBoxJoin.create({
                    'MBJid': str(uuid.uuid1()),
                    'USid': usid,
                    'MBAid': mbaid,
                    'MBJprice': magic_box_apply.SKUprice,
                })
                db.session.add(magic_box_join)
            else:
                # 但是可以多次分享
                if magic_box_join.MBJstatus == ActivityRecvStatus.ready_recv.value:
                    raise StatusError('本期已参与')
        return Success('参与成功', data={
            'mbjid': magic_box_join.MBJid
        })

    @token_required
    def recv_award(self):
        """购买魔盒礼品"""
        self.wx_pay = wx_pay

        form = MagicBoxRecvAwardForm().valid_data()
        # magic_box_join = form.magic_box_join
        mbaid = form.mbaid.data

        omclient = form.omclient.data
        ommessage = form.ommessage.data
        opaytype = form.opaytype.data
        uaid = form.uaid.data
        usid = request.user.id
        magic_box_join = MagicBoxJoin.query.filter_by_({'MBAid': mbaid, 'USid': usid}).first_('未参与')
        if magic_box_join and magic_box_join.MBJstatus != ActivityRecvStatus.wait_recv.value:
            raise StatusError('本期已领奖')

        with db.auto_commit():
            magic_box_apply = MagicBoxApply.query.filter_by_({"MBAid": mbaid}).first()
            prid = magic_box_apply.PRid
            skuid = magic_box_apply.SKUid
            price = magic_box_join.MBJcurrentPrice
            pbid = magic_box_apply.PBid
            current_app.logger.info(pbid)
            product_brand = ProductBrand.query.filter_by({"PBid": pbid}).first()
            product = Products.query.filter_by({'PRid': prid}).first()
            sku = ProductSku.query.filter_by({'SKUid': magic_box_apply.SKUid}).first()
            # 地址信息
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
                'OMfrom': OrderFrom.magic_box.value,
                'PBname': product_brand.PBname,
                'PBid': pbid,
                'OMclient': omclient,
                'OMfreight': 0,  # 运费暂时为0
                'OMmount': price,
                'OMmessage': ommessage,
                'OMtrueMount': price,
                # 收货信息
                'OMrecvPhone': omrecvphone,
                'OMrecvName': omrecvname,
                'OMrecvAddress': omrecvaddress,
                'PRcreateId': product.CreaterId,
            }
            order_main_instance = OrderMain.create(order_main_dict)
            db.session.add(order_main_instance)
            # 订单副单
            user = get_current_user()
            order_part_dict = {
                'OMid': omid,
                'OPid': str(uuid.uuid1()),
                'SKUid': skuid,
                'PRattribute': product.PRattribute,
                'SKUattriteDetail': sku.SKUattriteDetail,
                'PRtitle': product.PRtitle,
                'SKUprice': price,
                'PRmainpic': product.PRmainpic,
                'OPnum': 1,
                'PRid': product.PRid,
                'OPsubTotal': price,
                # 副单商品来源
                'PRfrom': product.PRfrom,
                'UPperid': user.USsupper1,
                'UPperid2': user.USsupper2,
                # todo 活动佣金设置
            }
            order_part_instance = OrderPart.create(order_part_dict)
            db.session.add(order_part_instance)
            # 用户参与状态改变
            magic_box_join.MBJstatus = ActivityRecvStatus.ready_recv.value
            db.session.add(magic_box_join)
            # 支付数据表
            order_pay_dict = {
                'OPayid': str(uuid.uuid1()),
                'OPayno': opayno,
                'OPayType': opaytype,
                'OPayMount': price,
            }
            order_pay_instance = OrderPay.create(order_pay_dict)
            db.session.add(order_pay_instance)
        # 生成支付信息
        body = product.PRtitle
        openid = user.USopenid1 or user.USopenid2
        pay_args = self._pay_detail(omclient, opaytype, opayno, float(price), body, openid=openid)
        response = {
            'pay_type': PayType(opaytype).name,
            'opaytype': opaytype,
            'args': pay_args
        }
        return Success('创建订单成功', data=response)



