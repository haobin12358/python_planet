import random
import uuid
from datetime import date, datetime, timedelta
from decimal import Decimal

from flask import current_app
from sqlalchemy.dialects.postgresql import json

from planet.common.error_response import StatusError, DumpliError, NotFound, AuthorityError
from planet.common.params_validates import parameter_required
from planet.common.success_response import Success
from planet.common.token_handler import token_required, get_current_user, is_supplizer, is_admin
from planet.config.enums import ApplyStatus, ActivityType, ActivityRecvStatus, OrderFrom, PayType, ProductStatus, \
    ApplyFrom
from planet.extensions.register_ext import db, wx_pay
from planet.extensions.validates.activty import MagicBoxOpenForm, ParamsError, MagicBoxJoinForm, request, \
    MagicBoxRecvAwardForm
from planet.models import MagicBoxJoin, MagicBoxApply, GuessNumAwardApply, MagicBoxOpen, User, Activity, ProductBrand, \
    AddressArea, UserAddress, AddressCity, AddressProvince, OrderMain, Products, OrderPart, ProductSku, OrderPay, \
    Approval, ProductImage, ProductSkuValue, Supplizer, Admin, MagicBoxFlow, OutStock
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
            out_stock = OutStock.query.filter(
                OutStock.OSid == magic_box_apply.OSid
            ).first()
            if out_stock.OSnum is not None:
                out_stock.OSnum = out_stock.OSnum - 1
                if out_stock.OSnum < 0:
                    raise StatusError('库存不足, 活动结束')
                db.session.flush()
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
            suid = magic_box_apply.SUid if magic_box_apply.MBAfrom else None
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
                'PRcreateId': suid,
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
            # 记录订单
            db.session.add(MagicBoxFlow.create({
                'MBFid': str(uuid.uuid1()),
                'OMid': omid,
                'MBJid': magic_box_join.MBJid
            }))
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

    def list(self):
        """查看自己的申请列表"""
        if is_supplizer():
            suid = request.user.id
        elif is_admin():
            suid = None
        else:
            raise AuthorityError()
        data = parameter_required()
        mbastatus = data.get('mbastatus', 'all')
        if str(mbastatus) == 'all':
            mbastatus = None
        else:
            mbastatus = getattr(ApplyStatus, mbastatus).value
        starttime, endtime = data.get('starttime', '2019-01-01'), data.get('endtime', '2100-01-01')
        out_stocks_query = OutStock.query.join(MagicBoxApply,
                                               MagicBoxApply.OSid == OutStock.OSid
                                               ).group_by(OutStock.OSid).order_by(MagicBoxApply.MBAstarttime.desc(),
                                                                                  MagicBoxApply.createtime.desc())
        if suid:
            out_stocks_query = out_stocks_query.filter(MagicBoxApply.SUid == suid)
        out_stocks = out_stocks_query.all()
        award_list = []
        for out_stock in out_stocks:
            awards = MagicBoxApply.query.filter(MagicBoxApply.isdelete == False,
                                                MagicBoxApply.OSid == out_stock.OSid
                                                ).filter_(MagicBoxApply.MBAstatus == mbastatus,
                                                          MagicBoxApply.MBAstarttime >= starttime,
                                                          MagicBoxApply.MBAstarttime <= endtime
                                                          ).all()
            for award in awards:
                award.fill('skustock', out_stock.OSnum)
            award_list.extend(awards)

        for award in award_list:
            award.Gearsone = json.loads(award.Gearsone)
            award.Gearstwo = json.loads(award.Gearstwo)
            award.Gearsthree = json.loads(award.Gearsthree)
            sku = ProductSku.query.filter_by(SKUid=award.SKUid).first()
            award.fill('skupic', sku['SKUpic'])
            product = Products.query.filter_by(PRid=award.PRid).first()
            award.fill('prtitle', product.PRtitle)
            award.fill('prmainpic', product['PRmainpic'])
            brand = ProductBrand.query.filter_by(PBid=product.PBid).first()
            award.fill('pbname', brand.PBname)
            award.fill('mbastatus_zh', ApplyStatus(award.MBAstatus).zh_value)
            if award.MBAfrom == ApplyFrom.supplizer.value:
                sup = Supplizer.query.filter_by(SUid=award.SUid).first()
                name = getattr(sup, 'SUname', '')
            elif award.MBAfrom == ApplyFrom.platform.value:
                admin = Admin.query.filter_by(ADid=award.SUid).first()
                name = getattr(admin, 'ADname', '')
            else:
                name = ''
            award.fill('authname', name)
            award.fill('createtime', award.createtime)

        # 筛选后重新分页
        page = int(data.get('page_num', 1)) or 1
        count = int(data.get('page_size', 15)) or 15
        total_count = len(award_list)
        if page < 1:
            page = 1
        total_page = int(total_count / int(count)) or 1
        start = (page - 1) * count
        if start > total_count:
            start = 0
        if total_count / (page * count) < 0:
            ad_return_list = award_list[start:]
        else:
            ad_return_list = award_list[start: (page * count)]
        request.page_all = total_page
        request.mount = total_count
        return Success(data=ad_return_list)

    def apply_award(self):
        """申请添加魔盒奖品"""
        if not (is_supplizer() or is_admin()):
            raise AuthorityError()
        data = parameter_required(('skuid', 'prid', 'skustock', 'mbastarttime', 'skuprice',
                                   'skuminprice', 'gearsone', 'gearstwo', 'gearsthree'))
        skuid, prid, skustock = data.get('skuid'), data.get('prid'), data.get('skustock', 1)
        gearsone, gearstwo, gearsthree = data.get('gearsone'), data.get('gearstwo'), data.get('gearsthree')
        if not isinstance(gearsone, list):
            raise ParamsError('gearsone格式错误')
        elif not isinstance(gearstwo, list):
            raise ParamsError('gearstwo格式错误')
        elif not isinstance(gearsthree, list):
            raise ParamsError('gearsthree格式错误')
        gearsone, gearstwo, gearsthree = json.dumps(gearsone), json.dumps(gearstwo), json.dumps(gearsthree)
        mbafrom = ApplyFrom.supplizer.value if is_supplizer() else ApplyFrom.platform.value
        sku = ProductSku.query.filter_by_(SKUid=skuid).first_('没有该skuid信息')
        product = Products.query.filter(Products.PRid == prid, Products.isdelete == False,
                                        Products.PRstatus == ProductStatus.usual.value
                                        ).first_('当前商品状态不允许进行申请')
        assert sku.PRid == prid, 'sku与商品信息不对应'

        # 将申请事物时间分割成每天单位
        # begin_time = str(data.get('mbastarttime'))[:10]
        # end_time = str(data.get('mbaendtime'))[:10]
        # time_list = self._getBetweenDay(begin_time, end_time)

        time_list = data.get('mbastarttime')
        if not isinstance(time_list, list):
            raise ParamsError('参数 mbastarttime 格式错误')
        award_instance_list = list()
        mbaid_list = list()
        skustock = int(skustock)
        with db.auto_commit():
            # 活动出库单
            osid = str(uuid.uuid1())
            db.session.add(OutStock.create({
                'OSid': osid,
                'SKUid': skuid,
                'OSnum': skustock
            }))
            self._update_stock(-skustock, skuid=skuid)
            for day in time_list:
                # 先检测是否存在相同skuid,相同日期的申请
                exist_apply_sku = MagicBoxApply.query.filter(MagicBoxApply.SKUid == skuid,
                                                             MagicBoxApply.isdelete == False,
                                                             MagicBoxApply.SUid == request.user.id,
                                                             MagicBoxApply.MBAstarttime == day).first()
                if exist_apply_sku:
                    raise ParamsError('您已添加过{}日的申请'.format(day))
                award_dict = {
                    'MBAid': str(uuid.uuid1()),
                    'SUid': request.user.id,
                    'SKUid': skuid,
                    'PRid': prid,
                    'PBid': product.PBid,
                    'MBAstarttime': day,
                    'MBAendtime': day,
                    'SKUprice': float(data.get('skuprice', 0.01)),
                    'SKUminPrice': float(data.get('skuminprice', 0.01)),
                    'Gearsone': gearsone,
                    'Gearstwo': gearstwo,
                    'Gearsthree': gearsthree,
                    # 'SKUstock': int(skustock),
                    "OSid": osid,
                    'MBAstatus': ApplyStatus.wait_check.value,
                    'MBAfrom': mbafrom,
                }
                award_instance = MagicBoxApply.create(award_dict)
                award_instance_list.append(award_instance)
                mbaid_list.append(award_dict['MBAid'])
            db.session.add_all(award_instance_list)
            # 添加到审批流
            [super().create_approval('tomagicbox', request.user.id, mbaid, mbafrom) for mbaid in mbaid_list]
        return Success('申请添加成功', {'mbaid': mbaid_list})

    def update_apply(self):
        """修改魔盒申请"""
        if not (is_supplizer() or is_admin()):
            raise AuthorityError()
        data = parameter_required(('skuid', 'prid', 'skustock', 'mbastarttime', 'skuprice',
                                   'skuminprice', 'gearsone', 'gearstwo', 'gearsthree'))
        mbaid, skuid, prid, skustock = data.get('mbaid'), data.get('skuid'), data.get('prid'), data.get('skustock')
        gearsone, gearstwo, gearsthree = data.get('gearsone'), data.get('gearstwo'), data.get('gearsthree')
        if not isinstance(gearsone, list):
            raise ParamsError('gearsone格式错误')
        elif not isinstance(gearstwo, list):
            raise ParamsError('gearstwo格式错误')
        elif not isinstance(gearsthree, list):
            raise ParamsError('gearsthree格式错误')
        gearsone, gearstwo, gearsthree = json.dumps(gearsone), json.dumps(gearstwo), json.dumps(gearsthree)
        apply_info = MagicBoxApply.query.filter(MagicBoxApply.MBAid == mbaid,
                                                MagicBoxApply.MBAstatus.in_([ApplyStatus.reject.value,
                                                                            ApplyStatus.cancle.value])
                                                ).first_('只有已拒绝或撤销状态下的申请可以进行修改')

        if apply_info.SUid != request.user.id:
            raise AuthorityError('仅可修改自己提交的申请')
        mbafrom = ApplyFrom.supplizer.value if is_supplizer() else ApplyFrom.platform.value
        sku = ProductSku.query.filter_by_(SKUid=skuid).first_('没有该skuid信息')
        product = Products.query.filter(Products.PRid == prid, Products.isdelete == False,
                                        Products.PRstatus == ProductStatus.usual.value
                                        ).first_('仅可将已上架的商品用于申请')  # 当前商品状态不允许进行申请

        assert sku.PRid == prid, 'sku与商品信息不对应'
        with db.auto_commit():
            award_dict = {
                'SUid': request.user.id,
                'SKUid': skuid,
                'PRid': prid,
                'PBid': product.PBid,
                'MBAstarttime': data.get('mbastarttime'),
                'MBAendtime': data.get('mbastarttime'),
                'SKUprice': float(data.get('skuprice', 0.01)),
                'SKUminPrice': float(data.get('skuminprice', 0.01)),
                'Gearsone': gearsone,
                'Gearstwo': gearstwo,
                'Gearsthree': gearsthree,
                # 'SKUstock': int(skustock),
                'MBAstatus': ApplyStatus.wait_check.value,
                'MBAfrom': mbafrom,
            }
            award_dict = {k: v for k, v in award_dict.items() if v is not None}
            MagicBoxApply.query.filter_by_(MBAid=mbaid).update(award_dict)
        super().create_approval('tomagicbox', request.user.id, mbaid, mbafrom)
        return Success('修改成功', {'mbaid': mbaid})

    def award_detail(self):
        """查看申请详情"""
        if not (is_supplizer() or is_admin()):
            args = parameter_required(('mbaid',))
            mbaid = args.get('mbaid')
            award = MagicBoxApply.query.filter_by_(MBAid=mbaid).first_('该申请已被删除')
            award.Gearsone = json.loads(award.Gearsone)
            award.Gearstwo = json.loads(award.Gearstwo)
            award.Gearsthree = json.loads(award.Gearsthree)
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
        data = parameter_required(('mbaid',))
        mbaid = data.get('mbaid')
        with db.auto_commit():
            apply_info = MagicBoxApply.query.filter_by_(MBAid=mbaid).first_('无此申请记录')
            other_apply_info = MagicBoxApply.query.filter(
                MagicBoxApply.isdelete == False,
                MagicBoxApply.MBAid != mbaid,
                MagicBoxApply.OSid == apply_info.OSid,
            ).first()
            if apply_info.MBAstatus != ApplyStatus.wait_check.value:
                raise StatusError('只有在审核状态的申请可以撤销')
            if apply_info.SUid != request.user.id:
                raise AuthorityError('仅可撤销自己提交的申请')
            apply_info.MBAstatus = ApplyStatus.cancle.value
            # 是否修改库存
            if not other_apply_info:
                out_stock = OutStock.query.filter(
                    OutStock.isdelete == False,
                    OutStock.OSid == apply_info.OSid
                ).first()
                self._update_stock(out_stock.OSnum, skuid=apply_info.SKUid)
            # 同时将正在进行的审批流改为取消
            approval_info = Approval.query.filter_by_(AVcontent=mbaid, AVstartid=request.user.id,
                                                      AVstatus=ApplyStatus.wait_check.value).first()
            approval_info.AVstatus = ApplyStatus.cancle.value
        return Success('取消成功', {'mbaid': mbaid})

    def delete_apply(self):
        """删除申请"""
        if is_supplizer():
            usid = request.user.id
            sup = Supplizer.query.filter_by_(SUid=usid).first_('供应商信息错误')
            current_app.logger.info('Supplizer {} delete magicbox apply'.format(sup.SUname))
        elif is_admin():
            usid = request.user.id
            admin = Admin.query.filter_by_(ADid=usid).first_('管理员信息错误')
            current_app.logger.info('Admin {} magicbox apply'.format(admin.ADname))
            sup = None
        else:
            raise AuthorityError()
        data = parameter_required(('mbaid',))
        mbaid = data.get('mbaid')
        with db.auto_commit():
            apply_info = MagicBoxApply.query.filter_by_(MBAid=mbaid).first_('无此申请记录')
            if sup:
                assert apply_info.SUid == usid, '供应商只能删除自己提交的申请'
            if apply_info.MBAstatus not in [ApplyStatus.cancle.value, ApplyStatus.reject.value]:
                raise StatusError('只能删除已拒绝或已撤销状态下的申请')
            apply_info.isdelete = True
        return Success('删除成功', {'mbaid': mbaid})

    def shelves(self):
        """下架申请"""
        if is_supplizer():
            usid = request.user.id
            sup = Supplizer.query.filter_by_(SUid=usid).first_('供应商信息错误')
            current_app.logger.info('Supplizer {} delete magicbox apply'.format(sup.SUname))
        elif is_admin():
            usid = request.user.id
            admin = Admin.query.filter_by_(ADid=usid).first_('管理员信息错误')
            current_app.logger.info('Admin {} magicbox apply'.format(admin.ADname))
            sup = None
        else:
            raise AuthorityError()
        data = parameter_required(('mbaid',))
        mbaid = data.get('mbaid')
        with db.auto_commit():
            apply_info = MagicBoxApply.query.filter_by_(MBAid=mbaid).first_('无此申请记录')
            if sup:
                assert apply_info.SUid == usid, '供应商只能下架自己的申请'
            if apply_info.MBAstatus != ApplyStatus.agree.value:
                raise StatusError('只能下架已通过的申请')
            apply_info.MBAstatus = ApplyStatus.reject.value
        return Success('下架成功', {'mbaid': mbaid})

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
