import random
import re
import uuid
from datetime import date, datetime, timedelta
from decimal import Decimal

from flask import current_app, request
from sqlalchemy import func
from sqlalchemy.dialects.postgresql import json

from planet.common.error_response import StatusError, DumpliError, NotFound, AuthorityError, ParamsError
from planet.common.params_validates import parameter_required
from planet.common.success_response import Success
from planet.common.token_handler import token_required, is_supplizer, is_admin, common_user, is_tourist
from planet.config.enums import ApplyStatus, ActivityType, OrderFrom, PayType, ProductStatus, \
    ApplyFrom, AdminActionS, ProductFrom, ProductBrandStatus, MagicBoxJoinStatus, MagicBoxOpenAction, \
    ActivityDepositStatus, Client, OrderMainStatus
from planet.control.BaseControl import BASEADMIN, BASEAPPROVAL
from planet.extensions.register_ext import db, wx_pay
from planet.models import MagicBoxJoin, MagicBoxApply, MagicBoxOpen, User, Activity, ProductBrand, \
    AddressArea, UserAddress, AddressCity, AddressProvince, OrderMain, Products, OrderPart, ProductSku, OrderPay, \
    Approval, ProductImage, Supplizer, Admin, ProductCategory, MagicBoxApplySku, ActivityDeposit
from .COrder import COrder


class CMagicBox(COrder, BASEAPPROVAL):

    def get(self):
        """商品/盒子详情"""
        args = request.args.to_dict()
        mbaid, mbjid, mbj = args.get('mbaid'), args.get('mbjid'), None
        if not mbaid and not mbjid:
            raise ParamsError(' mbaid / mbjid 至少需要其一')
        if mbjid:
            mbj = MagicBoxJoin.query.filter(MagicBoxJoin.MBJid == mbjid,
                                            MagicBoxJoin.isdelete == False).first_('该礼盒活动已结束')
            mbaid = mbj.MBAid

        agree_status = MagicBoxApply.MBAstatus == ApplyStatus.agree.value
        filter_args = [MagicBoxApply.isdelete == False, MagicBoxApply.MBAid == mbaid]
        if common_user() or is_tourist():
            filter_args.append(agree_status)
        try:
            if mbj and mbj.MBJstatus == MagicBoxJoinStatus.completed.value and agree_status in filter_args:
                filter_args.remove(agree_status)
            mba = MagicBoxApply.query.filter(*filter_args).first_('该礼盒商品已下架')
            product = self._fill_mba(mba)
        except Exception as e:
            current_app.logger.error('The error is {}'.format(e))
            raise StatusError('该礼盒商品已下架')

        product.fill('rules', db.session.query(Activity.ACdesc
                                               ).filter_by_(ACtype=ActivityType.magic_box.value).scalar())
        currentprice = records = have_paid = trade = lowest = None
        if mbj:
            # 有mbj 的情况下，重新显示 可购 原价 当前价 最低价
            currentprice = mbj.MBJcurrentPrice
            product.fill('PRprice', mbj.MBJprice)
            product.fill('mbjid', mbj.MBJid)
            product.fill('mbjstatus', mbj.MBJstatus)
            product.fill('mbjstatus_en', MagicBoxJoinStatus(mbj.MBJstatus).name)
            product.fill('mbjstatus_zh', MagicBoxJoinStatus(mbj.MBJstatus).zh_value)
            product.fill('mbadeposit', mbj.LowestPrice)  # 押金 (最低价)
            product.fill('purchaseprice', mbj.HighestPrice)  # 可购价
            product.fill('selectedsku', mbj.MBSid)  # 已选的sku
            spreadprice = None
            records = MagicBoxOpen.query.filter_by_(MBJid=mbj.MBJid
                                                    ).order_by(MagicBoxOpen.createtime.asc()).all()

            if common_user():
                if ActivityDeposit.query.filter(ActivityDeposit.isdelete == False,
                                                ActivityDeposit.ACtype == ActivityType.magic_box.value,
                                                ActivityDeposit.ACDstatus == ActivityDepositStatus.valid.value,
                                                ActivityDeposit.ACDcontentId == mbaid,
                                                ActivityDeposit.ACDid == mbj.ACDid,
                                                ActivityDeposit.USid == request.user.id
                                                ).first():
                    have_paid = True
                spreadprice = float(currentprice) - float(mbj.LowestPrice)
                lowest = True if spreadprice <= 0 else False
                trade = True if currentprice <= mbj.HighestPrice else False
                spreadprice = 0 if spreadprice <= 0 else round(spreadprice, 2)

            product.fill('spreadprice', spreadprice)  # 需要补的差价

            gearlevel = {'1': 'A', '2': 'B', '3': 'C'}

            for mbjr in records:
                mbjr.fields = ['MBJid', 'createtime', 'USheader']
                action = MagicBoxOpenAction(mbjr.MBOaction).zh_value
                record_str = '{}帮拆礼盒{}, {}{}元, 当前{}元'.format(mbjr.USname,
                                                            gearlevel.get(str(mbjr.MBOgear)),
                                                            action, mbjr.MBOresult, mbjr.MBOprice)
                if mbjr.MBOresult == 0:
                    if mbjr.MBOaction == MagicBoxOpenAction.increase.value:
                        record_str = '{}帮拆礼盒{}，已是最高价，增加了0元，当前{}元'.format(mbjr.USname,
                                                                         gearlevel.get(str(mbjr.MBOgear)),
                                                                         mbjr.MBOprice)
                    else:
                        record_str = '{}帮拆礼盒{}，已是最低价，减少了0元，当前{}元'.format(mbjr.USname,
                                                                         gearlevel.get(str(mbjr.MBOgear)),
                                                                         mbjr.MBOprice)

                mbjr.fill('record_str', record_str)
        product.fill('currentprice', currentprice)
        product.fill('records', records)

        product.fill('topaydeposit', bool(not have_paid))  # 是否已付押金
        product.fill('trade', bool(trade))  # 是否可以购买
        product.fill('lowest', bool(lowest))  # 是否已达最大优惠

        return Success(data=product)

    def _fill_mba(self, mba):
        product = Products.query.filter(Products.PRid == mba.PRid, Products.isdelete == False).first_('商品已下架')
        product.fields = ['PRid', 'PRtitle', 'PRprice', 'PRlinePrice', 'PRsalesValue', 'PRstatus', 'PRmainpic',
                          'PRattribute', 'PRdesc', 'PRdescription']
        if isinstance(product.PRattribute, str):
            product.PRattribute = json.loads(product.PRattribute)
        if isinstance(getattr(product, 'PRremarks', None) or '{}', str):
            product.PRremarks = json.loads(getattr(product, 'PRremarks', None) or '{}')
        pb = ProductBrand.query.filter_by(PBid=product.PBid, isdelete=False).first()
        pb.fields = ['PBname', 'PBid']

        images = ProductImage.query.filter(
            ProductImage.PRid == product.PRid, ProductImage.isdelete == False).order_by(
            ProductImage.PIsort).all()
        [img.hide('PRid') for img in images]
        product.fill('images', images)
        product.fill('brand', pb)

        mbs_list = MagicBoxApplySku.query.filter_by(isdelete=False, MBAid=mba.MBAid).all()
        depost_price = []
        skus = []
        sku_value_item = []
        for mbs in mbs_list:
            depost_price.append([round(float(mbs.LowestPrice), 2), round(float(mbs.HighestPrice), 2)])
            sku = ProductSku.query.filter_by(SKUid=mbs.SKUid, isdelete=False).first()
            if not sku:
                current_app.logger.error('该商品sku已删除 skuid = {0}'.format(mbs.SKUid))
                continue
            sku.hide('SKUstock', 'SkudevideRate', 'PRid')
            sku.fill('skuprice', mbs.SKUprice)
            sku.fill('mbsstock', mbs.MBSstock)
            sku.fill('mbsid', mbs.MBSid)
            sku.fill('highestprice', mbs.HighestPrice)
            sku.fill('lowestprice', mbs.LowestPrice)

            if isinstance(sku.SKUattriteDetail, str):
                sku.SKUattriteDetail = json.loads(sku.SKUattriteDetail)
            sku_value_item.append(sku.SKUattriteDetail)
            skus.append(sku)
        if not skus:
            current_app.logger.error('该申请的商品没有sku prid = {0}'.format(product.PRid))
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
        product.fill('skuvalue', sku_value_item_reverse)
        product.fill('mbastatus', mba.MBAstatus)
        product.fill('mbastatus_en', ApplyStatus(mba.MBAstatus).name)
        product.fill('mbastatus_zh',  ApplyStatus(mba.MBAstatus).zh_value)
        product.fill('mbadeposit', min(depost_price)[0])  # 押金
        product.fill('purchaseprice', min(depost_price)[1])  # 可购价
        product.fill('mbaid', mba.MBAid)
        product.fill('mbaday', mba.MBAday)
        product.fill('mbarejectreason', mba.MBArejectReason)
        product.fill('mbafreight', mba.MBAfreight)
        gearone = gearone_str = geartwo = geartwo_str = gearthree = gearthree_str = None
        if isinstance(mba.Gearsone, str):
            gearone = json.loads(mba.Gearsone)
            gearone_str = f'礼盒A：随机减少{gearone[0]}元'
        if isinstance(mba.Gearstwo, str):
            geartwo = json.loads(mba.Gearstwo)
            geartwo_str = f'礼盒B：随机减少{geartwo[0]}元或增加{geartwo[1]}元'
        if isinstance(mba.Gearsthree, str):
            gearthree = json.loads(mba.Gearsthree)
            gearthree_str = f'礼盒C：随机减少{gearthree[0]}元或增加{gearthree[1]}元'
        product.fill('gearsone', gearone)
        product.fill('gearone_str', gearone_str)
        product.fill('gearstwo', geartwo)
        product.fill('geartwo_str', geartwo_str)
        product.fill('gearsthree', gearthree)
        product.fill('gearthree_str', gearthree_str)
        return product

    @staticmethod
    def _filter_my_box():
        usid = request.user.id
        res = MagicBoxJoin.query.filter(MagicBoxJoin.isdelete == False,
                                        MagicBoxJoin.USid == usid
                                        ).order_by(func.field(MagicBoxJoin.MBJstatus, 0, 10, -10),
                                                   MagicBoxJoin.createtime.desc())
        return res

    @staticmethod
    def _fill_header_record(mbj):
        mbos = MagicBoxOpen.query.filter(MagicBoxOpen.isdelete == False,
                                         MagicBoxOpen.MBJid == mbj.MBJid,
                                         ).order_by(MagicBoxOpen.createtime.desc()).all()
        headers = [mb.USheader for mb in mbos]
        record = '已有{}人帮拆'.format(len(mbos))
        if not mbos:
            record = '邀请好友帮拆'
        if mbj.MBJstatus == MagicBoxJoinStatus.completed.value:
            record = '已购买商品'
        elif mbj.MBJstatus == MagicBoxJoinStatus.expired.value:
            record = '活动已结束'
        return headers, record

    def _fill_single_box(self, mbj):
        mbj.fields = ['MBJid', 'MBJstatus', 'MBJcurrentPrice', 'MBSendtime', 'PRtitle', 'PRmainpic']
        mbj.fill('MBJstatus_en', MagicBoxJoinStatus(getattr(mbj, 'MBJstatus', 0)).name)
        mbj.fill('MBJstatus_zh', MagicBoxJoinStatus(getattr(mbj, 'MBJstatus', 0)).zh_value)
        mbj.fill('mbadeposit', mbj.LowestPrice)
        headers, record = self._fill_header_record(mbj)
        mbj.fill('headers', headers)
        mbj.fill('record', record)

    @staticmethod
    def _back_box_product_list(mbastatus, starttime, endtime):
        filter_args = []
        try:
            mbastatus = getattr(ApplyStatus, mbastatus).value
        except Exception:
            mbastatus = None
        if isinstance(mbastatus, int):
            filter_args.append(MagicBoxApply.MBAstatus == mbastatus)
        if is_supplizer():
            filter_args.append(MagicBoxApply.SUid == request.user.id)

        mbas = MagicBoxApply.query.filter(MagicBoxApply.isdelete == False,
                                          MagicBoxApply.MBAday >= starttime,
                                          MagicBoxApply.MBAday <= endtime,
                                          *filter_args
                                          ).order_by(MagicBoxApply.createtime.desc()
                                                     ).all_with_page()
        for mba in mbas:
            mba.hide('SUid', 'MBAfreight')
            product = Products.query.filter(Products.PRid == mba.PRid, Products.isdelete == False).first()
            pbname = db.session.query(ProductBrand.PBname).filter_by_(isdelete=False, PBid=product.PBid).scalar()
            mba.fill('pbname', pbname)
            mba.Gearsone = json.loads(mba.Gearsone)
            mba.Gearstwo = json.loads(mba.Gearstwo)
            mba.Gearsthree = json.loads(mba.Gearsthree)
            mba.fill('mbastatus_en', ApplyStatus(mba.MBAstatus).name)
            mba.fill('mbastatus_zh', ApplyStatus(mba.MBAstatus).zh_value)
            if not product:
                continue
            mbs_list = MagicBoxApplySku.query.filter(MagicBoxApplySku.isdelete == False,
                                                     MagicBoxApplySku.MBAid == mba.MBAid).all()
            for mbs in mbs_list:
                product_sku = ProductSku.query.filter_by(SKUid=mbs.SKUid, isdelete=False).first()
                if not product_sku:
                    continue
                mbs.fill('skuattritedetail', json.loads(getattr(product_sku, 'SKUattriteDetail', '')))
            mba.fill('skus', mbs_list)
            mba.fill('prtitle', product.PRtitle)
            mba.fill('prmainpic', product['PRmainpic'])
        return Success(data=mbas)

    def list(self):
        """魔盒/商品列表"""
        args = request.args.to_dict()
        now = datetime.now()
        option = args.get('option')
        mbastatus = args.get('mbastatus')
        starttime, endtime = (args.get('starttime', '2019-01-01') or '2019-01-01',
                              args.get('endtime', '2100-01-01') or '2100-01-01')

        if is_admin() or is_supplizer():
            return self._back_box_product_list(mbastatus, starttime, endtime)
        if str(option) == 'my':
            my_box = []
            if common_user():
                my_box = self._filter_my_box().all_with_page()
                list(map(lambda x: self._fill_single_box(x), my_box))
            return Success(data=my_box)

        my_box = []
        if common_user():
            my_box = self._filter_my_box().distinct().limit(2).all()
            list(map(lambda x: self._fill_single_box(x), my_box))
        box_product = MagicBoxApply.query.filter(MagicBoxApply.isdelete == False,
                                                 MagicBoxApply.MBAday == now.date(),
                                                 MagicBoxApply.MBAstatus == ApplyStatus.agree.value
                                                 ).order_by(MagicBoxApply.createtime.desc()).all_with_page()
        for box in box_product:
            box.fields = ['MBAid', 'MBAday', 'MBAstatus']
            product = Products.query.filter(Products.PRid == box.PRid, Products.isdelete == False).first()
            if not product:
                continue
            mbssku_list = MagicBoxApplySku.query.filter_by_(MBAid=box.MBAid).all()
            mbssku_price = [mbs.LowestPrice for mbs in mbssku_list]
            box.fill('prtitle', product.PRtitle)
            box.fill('prmainpic', product['PRmainpic'])
            box.fill('mbadeposit', min(mbssku_price))
        res = {'mybox': my_box,
               'box_product': box_product}
        return Success(data=res)

    @token_required
    def open(self):
        """好友帮拆"""
        usid = request.user.id
        user = User.query.filter_by_(USid=usid).first_('请重新登录')
        data = parameter_required(('mbjid', 'level'))
        mbjid, level = data.get('mbjid'), data.get('level')
        if not re.match(r'^[123]$', str(level)):
            raise ParamsError('level 参数错误')

        levle_attr = {'1': 'Gearsone', '2': 'Gearstwo', '3': 'Gearsthree'}.get(level)

        magic_box_join = MagicBoxJoin.query.filter_by(isdelete=False, MBJid=mbjid,
                                                      MBJstatus=MagicBoxJoinStatus.pending.value
                                                      ).first_('该礼盒活动已结束')
        if magic_box_join.USid == user.USid:
            raise NotFound('不能给自己拆盒子, 快去找小伙伴帮忙吧 ~')
        mbaid = magic_box_join.MBAid
        # 活动是否在进行
        magic_box_apply = MagicBoxApply.query.filter(MagicBoxApply.MBAid == mbaid,
                                                     MagicBoxApply.MBAstatus == ApplyStatus.agree.value
                                                     ).first_('该礼盒商品已下架')
        magic_box_sku = MagicBoxApplySku.query.filter_by_(MBSid=magic_box_join.MBSid).first()
        # sku_origin_price = db.session.query(ProductSku.SKUprice).filter_by_(SKUid=magic_box_sku.SKUid).scalar()
        with db.auto_commit():
            # 是否已经帮开奖
            ready_open = MagicBoxOpen.query.filter_by_(USid=usid, MBJid=mbjid).first()
            if ready_open:
                raise DumpliError('您已帮好友拆过该礼盒了')

            # 价格变动随机
            current_level_str = getattr(magic_box_apply, levle_attr)
            current_level_json = json.loads(current_level_str)  # 列表 ["1-2", "3-4"]
            current_level_json[0] = list(map(lambda x: int(x) * -1, current_level_json[0].split('-')))  # 第0个元素是-
            if len(current_level_json) == 2:
                current_level_json[1] = list(map(int, current_level_json[1].split('-')))  # 第1个元素是+

            if str(level) == '2':
                one = (current_level_json[0][1] - current_level_json[0][0]) * -1
                two = current_level_json[1][1] - current_level_json[1][0]
                probably = round(float(round(one/(one + two), 2) * 100), 2)
                current_app.logger.info('选择了 B 档，减价几率{}%'.format(probably))
                random_num = random.randint(0, 99)
                random_choice_first = current_level_json[0] if random_num < probably else current_level_json[1]
            elif str(level) == '3':
                one = (current_level_json[0][1] - current_level_json[0][0]) * -1
                two = current_level_json[1][1] - current_level_json[1][0]
                probably = round(float(round(one / (one + two), 2) * 100), 2)
                current_app.logger.info('选择了 C 档，减价几率{}%'.format(probably))
                random_num = random.randint(0, 99)
                random_choice_first = current_level_json[0] if random_num < probably else current_level_json[1]
            else:
                current_app.logger.info('选择了 A 档')
                random_choice_first = random.choice(current_level_json)  # 选择是- 还是+
            final_reduce = random.uniform(*random_choice_first)  # 最终价格变动
            final_reduce = round(Decimal(final_reduce), 2)
            current_app.logger.info('价格实际变动 {}'.format(final_reduce))

            if final_reduce < 0:
                action = MagicBoxOpenAction.reduce.value
            else:
                action = MagicBoxOpenAction.increase.value

            # 价格计算
            final_price = Decimal(magic_box_join.MBJcurrentPrice) + final_reduce
            if final_price < magic_box_sku.LowestPrice:
                final_price = magic_box_sku.LowestPrice
                final_reduce = Decimal(magic_box_sku.LowestPrice) - Decimal(magic_box_join.MBJcurrentPrice)
            if final_price >= Decimal(magic_box_sku.SKUprice):
                final_price = Decimal(magic_box_sku.SKUprice)
                final_reduce = Decimal(magic_box_sku.SKUprice) - Decimal(magic_box_join.MBJcurrentPrice)
            final_price = round(final_price, 2)

            if float(final_reduce) < 0:
                result = -1 * round(float(final_reduce), 2)
            else:
                result = round(float(final_reduce), 2)

            # 帮拆记录
            mb_open = MagicBoxOpen.create({
                'MBOid': str(uuid.uuid1()),
                'USid': usid,
                'USname': user.USname,
                'USheader': user.USheader,
                'MBJid': mbjid,
                'MBOgear': int(level),
                'MBOresult': result,
                'MBOaction': action,
                'MBOprice': float(final_price),
            })
            db.session.add(mb_open)

            # 源参与价格修改
            magic_box_join.MBJcurrentPrice = float(final_price)
        return Success('已成功助力', data={'action': action, 'final_reduce': result,
                                      'final_price': float(final_price)})

    @token_required
    def join(self):
        """支付押金，创建盒子"""
        data = parameter_required(('mbaid', 'mbsid'))
        usid = request.user.id
        user = User.query.filter_by_(USid=usid).first_("请重新登录")
        mbaid, mbsid = data.get('mbaid'), data.get('mbsid')
        opayno = wx_pay.nonce_str
        session_list = []
        with db.auto_commit():
            mba = MagicBoxApply.query.filter(MagicBoxApply.isdelete == False,
                                             MagicBoxApply.MBAstatus == ApplyStatus.agree.value,
                                             MagicBoxApply.MBAday == datetime.now().date(),
                                             MagicBoxApply.MBAid == mbaid).first_('该礼盒商品已下架')
            mbs = MagicBoxApplySku.query.filter(MagicBoxApplySku.MBAid == mba.MBAid,
                                                MagicBoxApplySku.isdelete == False,
                                                MagicBoxApplySku.MBSid == mbsid).first_('商品规格错误')
            product = Products.query.filter_by(isdelete=False, PRid=mba.PRid,
                                               PRstatus=ProductStatus.usual.value).first_('未找到该商品信息')
            price = mbs.LowestPrice
            depost = ActivityDeposit.create({
                'ACDid': str(uuid.uuid1()),
                'USid': user.USid,
                'ACtype': ActivityType.magic_box.value,
                'ACDdeposit': price,
                'ACDcontentId': mba.MBAid,
                'ACDstatus': ActivityDepositStatus.failed.value,
                'SKUid': mbs.MBSid,
                'OPayno': opayno
            })
            session_list.append(depost)

            # 支付数据表
            order_pay_dict = {
                'OPayid': str(uuid.uuid1()),
                'OPayno': opayno,
                'OPayType': PayType.wechat_pay.value,
                'OPayMount': price,
                'OPaymarks': '魔术礼盒押金'
            }
            order_pay_instance = OrderPay.create(order_pay_dict)
            session_list.append(order_pay_instance)
            db.session.add_all(session_list)

            # 生成支付信息
            omclient = Client.wechat.value
            opaytype = PayType.wechat_pay.value
            body = product.PRtitle
            openid = user.USopenid2
            pay_args = super(CMagicBox, self)._pay_detail(omclient, opaytype, opayno, round(float(price), 2), body, openid=openid)
            response = {
                'pay_type': PayType(opaytype).name,
                'opaytype': opaytype,
                'args': pay_args
            }
        return Success(data=response)

    @token_required
    def recv_award(self):
        """购买魔盒礼品"""
        data = parameter_required(('mbjid', 'uaid'))
        usid = request.user.id
        user = User.query.filter_by_(USid=usid).first_("请重新登录")
        mbjid = data.get('mbjid')
        uaid = data.get('uaid')
        ommessage = data.get('ommessage')
        omclient = Client.wechat.value
        opaytype = PayType.wechat_pay.value

        mbj = MagicBoxJoin.query.filter_by(isdelete=False, MBJid=mbjid, USid=usid,
                                           MBJstatus=MagicBoxJoinStatus.pending.value).first_('该礼盒活动已结束')
        if mbj.MBJcurrentPrice > mbj.HighestPrice:
            raise StatusError('还未达到可购价格哟，赶快邀请好友来帮忙吧 ~')
        mba = MagicBoxApply.query.filter(MagicBoxApply.isdelete == False, MagicBoxApply.MBAid == mbj.MBAid,
                                         MagicBoxApply.MBAstatus == ApplyStatus.agree.value).first_("该商品已下架")
        mbs = MagicBoxApplySku.query.filter_by(MBSid=mbj.MBSid, isdelete=False).first_('礼盒无此规格')

        if int(mbs.MBSstock) - 1 < 0:
            raise StatusError('商品库存不足')

        acdeposit = ActivityDeposit.query.filter_by(isdelete=False, ACDid=mbj.ACDid,
                                                    ACDstatus=ActivityDepositStatus.valid.value).first_('未找到相应押金')
        with db.auto_commit():
            prid = mba.PRid
            skuid = mbs.SKUid
            price = mbj.MBJcurrentPrice if float(mbj.MBJcurrentPrice) - float(acdeposit.ACDdeposit) >= 0 else acdeposit.ACDdeposit
            true_price = round(float(mbj.MBJcurrentPrice) - float(acdeposit.ACDdeposit), 2)  # 要补的差价
            redirect = False
            if true_price <= 0:
                # true_price = 0.01
                true_price = 0
                # price = round(float(acdeposit.ACDdeposit), 2) + 0.01
            product = Products.query.filter_by(PRid=prid, isdelete=False, PRstatus=ProductStatus.usual.value).first()
            pbid = product.PBid
            product_brand = ProductBrand.query.filter_by({"PBid": pbid}).first()
            product_category = ProductCategory.query.filter_by(PCid=product.PCid).first()
            sku = ProductSku.query.filter_by({'SKUid': skuid}).first()
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
            opayno = wx_pay.nonce_str

            product.PRsalesValue += 1  # 商品销量 +1
            mbs.MBSstock -= 1  # 库存 -1

            # 主单
            order_main_dict = {
                'OMid': omid,
                'OMno': super(CMagicBox, self)._generic_omno(),
                'OPayno': opayno,
                'USid': usid,
                'OMfrom': OrderFrom.magic_box.value,
                'PBname': product_brand.PBname,
                'PBid': pbid,
                'OMclient': omclient,
                'OMfreight': 0,  # 运费暂时为0
                'OMmount': mbs.SKUprice,
                'OMmessage': ommessage,
                'OMtrueMount': price,
                # 收货信息
                'OMrecvPhone': omrecvphone,
                'OMrecvName': omrecvname,
                'OMrecvAddress': omrecvaddress,
                'PRcreateId': product.CreaterId
            }
            if true_price <= 0:  # 不用支付差价时，直接生成订单并扣除押金
                order_main_dict['OMstatus'] = OrderMainStatus.wait_send.value
                mbj.update({'MBJstatus': MagicBoxJoinStatus.completed.value})
                acdeposit.update({'ACDstatus': ActivityDepositStatus.deduct.value})
                db.session.add(acdeposit)
                redirect = True
            order_main_instance = OrderMain.create(order_main_dict)
            db.session.add(order_main_instance)
            # 订单副单
            order_part_dict = {
                'OPid': str(uuid.uuid1()),
                'OMid': omid,
                'SKUid': mbs.MBSid,  # 魔盒商品的skuid
                'PRid': mba.MBAid,  # 魔盒商品id
                'PRattribute': product.PRattribute,
                'SKUattriteDetail': sku.SKUattriteDetail,
                'SKUprice': mbs.SKUprice,
                'PRtitle': product.PRtitle,
                'SKUsn': sku.SKUsn,
                'PCname': product_category.PCname,
                'PRmainpic': product.PRmainpic,
                'OPnum': 1,
                'OPsubTotal': price,
                'OPsubTrueTotal': price,
                'PRfrom': product.PRfrom,
                'SkudevideRate': sku.SkudevideRate,
                'UPperid': user.USsupper1,
                'UPperid2': user.USsupper2,
                'UPperid3': user.USsupper3,
                'USCommission1': user.USCommission1,
                'USCommission2': user.USCommission2,
                'USCommission3': user.USCommission3
            }
            order_part_instance = OrderPart.create(order_part_dict)
            db.session.add(order_part_instance)

            # 在盒子中记录omid，方便回调时更改盒子状态
            mbj.update({'OMid': omid})
            db.session.add(mbj)

            # 支付数据表
            order_pay_dict = {
                'OPayid': str(uuid.uuid1()),
                'OPayno': opayno,
                'OPayType': opaytype,
                'OPayMount': true_price,
            }
            order_pay_instance = OrderPay.create(order_pay_dict)
            db.session.add(order_pay_instance)

        from planet.extensions.tasks import auto_cancle_order
        auto_cancle_order.apply_async(args=([omid],), countdown=30 * 60, expires=40 * 60, )
        # 生成支付信息
        body = product.PRtitle
        openid = user.USopenid2
        pay_args = super(CMagicBox, self)._pay_detail(omclient, opaytype, opayno, float(true_price), body, openid=openid)
        response = {
            'pay_type': PayType(opaytype).name,
            'opaytype': opaytype,
            'args': pay_args,
            'redirect': redirect
        }
        return Success('创建订单成功', data=response)

    def apply_award(self):
        """申请添加魔盒商品"""
        if is_supplizer():
            sup = Supplizer.query.filter_by_(SUid=request.user.id).first_("账号状态错误")
        else:
            raise AuthorityError("仅可使用相应品牌供应商账号进行申请")
        data = parameter_required(('prid', 'mbaday', 'skus', 'gearsone', 'gearstwo', 'gearsthree'))
        prid, skus, mbaday = data.get('prid'), data.get('skus'), data.get('mbaday')
        gearsone, gearstwo, gearsthree = data.get('gearsone'), data.get('gearstwo'), data.get('gearsthree')
        gearsone_str, gearstwo_str, gearsthree_str = list(
            map(lambda x: self._check_gear_price(x), (gearsone, gearstwo, gearsthree)))
        if not isinstance(mbaday, list):
            raise ParamsError("mbaday 格式错误")

        instance_list, mbaid_list = [], []
        with db.auto_commit():
            product = Products.query.outerjoin(ProductBrand, ProductBrand.PBid == Products.PBid).filter(
                Products.PRid == prid,
                Products.isdelete == False,
                Products.PRstatus == ProductStatus.usual.value,
                Products.PRfrom == ProductFrom.supplizer.value,
                Products.CreaterId == sup.SUid,
                ProductBrand.isdelete == False,
                ProductBrand.PBstatus == ProductBrand.PBstatus == ProductBrandStatus.upper.value,
                ProductBrand.SUid == sup.SUid).first_('只能选择自己品牌下的商品')

            for day in mbaday:
                if datetime.strptime(day, '%Y-%m-%d').date() < datetime.now().date():
                    raise ParamsError('不允许申请当前时间之前的日期')
                exist_apply = MagicBoxApply.query.filter(MagicBoxApply.PRid == prid,
                                                         MagicBoxApply.isdelete == False,
                                                         MagicBoxApply.SUid == sup.SUid,
                                                         MagicBoxApply.MBAday == day).first()
                if exist_apply:
                    raise ParamsError('您已添加过该商品{}日的申请'.format(day))
                mba_instance = MagicBoxApply.create({
                    'MBAid': str(uuid.uuid1()),
                    'SUid': sup.SUid,
                    'PRid': prid,
                    'MBAday': day,
                    'Gearsone': gearsone_str,
                    'Gearstwo': gearstwo_str,
                    'Gearsthree': gearsthree_str,
                    'MBAstatus':  ApplyStatus.wait_check.value,
                })
                instance_list.append(mba_instance)
                mbaid_list.append(mba_instance.MBAid)
                for sku in skus:
                    parameter_required(('skuid', 'mbsstock', 'skuprice', 'highestprice', 'lowestprice'), datafrom=sku)
                    skuid, skuprice, mbsstock = sku.get('skuid'), sku.get('skuprice'), sku.get('mbsstock')
                    highestprice = sku.get('highestprice')
                    lowestprice = sku.get('lowestprice')
                    skuprice, highestprice, lowestprice = list(
                        map(lambda x: self._check_price(x), (skuprice, highestprice, lowestprice)))
                    if not (skuprice > highestprice > lowestprice):
                        raise ParamsError('请合理设置价格关系')
                    mbsstock = self._check_stock(mbsstock)
                    sku_instance = ProductSku.query.filter_by(isdelete=False, PRid=product.PRid,
                                                              SKUid=skuid).first_('商品sku信息不存在')
                    # 从原商品sku中减库存
                    super(CMagicBox, self)._update_stock(-mbsstock, product, sku_instance)

                    mbs_instance = MagicBoxApplySku.create({
                        'MBSid': str(uuid.uuid1()),
                        'MBAid': mba_instance.MBAid,
                        'SKUid': skuid,
                        'SKUprice': skuprice,
                        'MBSstock': mbsstock,
                        'HighestPrice': highestprice,
                        'LowestPrice': lowestprice
                    })
                    instance_list.append(mbs_instance)
            db.session.add_all(instance_list)
        [super(CMagicBox, self).create_approval('tomagicbox', sup.SUid, mbaid, ApplyFrom.supplizer.value
                                                ) for mbaid in mbaid_list]
        return Success('申请添加成功', {'mbaid': mbaid_list})

    def update_apply(self):
        """修改魔盒申请"""
        if is_supplizer():
            sup = Supplizer.query.filter_by_(SUid=request.user.id).first_("账号状态错误")
        else:
            raise AuthorityError('仅可编辑自己提交的申请')
        data = parameter_required(('mbaid', 'skus', 'gearsone', 'gearstwo', 'gearsthree'))
        mbaid, skus = data.get('mbaid'), data.get('skus')
        gearsone, gearstwo, gearsthree = data.get('gearsone'), data.get('gearstwo'), data.get('gearsthree')
        gearsone_str, gearstwo_str, gearsthree_str = list(
            map(lambda x: self._check_gear_price(x), (gearsone, gearstwo, gearsthree)))
        mba = MagicBoxApply.query.filter(MagicBoxApply.MBAid == mbaid,
                                         MagicBoxApply.isdelete == False,
                                         MagicBoxApply.MBAstatus.in_([ApplyStatus.cancle.value,
                                                                      ApplyStatus.reject.value,
                                                                      ApplyStatus.shelves.value])
                                         ).first_('当前状态不可进行编辑')

        product = Products.query.filter(Products.PRid == mba.PRid,
                                        Products.isdelete == False,
                                        Products.PRstatus == ProductStatus.usual.value,
                                        Products.CreaterId == sup.SUid,
                                        ).first_("当前商品状态不允许编辑")
        instance_list = []
        with db.auto_commit():
            mba.update({'Gearsone': gearsone_str,
                        'Gearstwo': gearstwo_str,
                        'Gearsthree': gearsthree_str,
                        'MBAstatus': ApplyStatus.wait_check.value})
            instance_list.append(mba)
            # 原sku全部删除
            MagicBoxApplySku.query.filter_by_(MBAid=mba.MBAid).delete_()
            # 接收新sku并重新扣除库存
            for sku in skus:
                parameter_required(('skuid', 'mbsstock', 'skuprice', 'highestprice', 'lowestprice'), datafrom=sku)
                skuid, skuprice, mbsstock = sku.get('skuid'), sku.get('skuprice'), sku.get('mbsstock')
                highestprice = sku.get('highestprice')
                lowestprice = sku.get('lowestprice')
                skuprice, highestprice, lowestprice = list(
                    map(lambda x: self._check_price(x), (skuprice, highestprice, lowestprice)))
                if not (skuprice > highestprice > lowestprice):
                    raise ParamsError('请合理设置价格关系')
                mbsstock = self._check_stock(mbsstock)
                sku_instance = ProductSku.query.filter_by(isdelete=False, PRid=product.PRid,
                                                          SKUid=skuid).first_('商品sku信息不存在')
                # 从原商品sku中减库存
                super(CMagicBox, self)._update_stock(-mbsstock, product, sku_instance)

                mbs_instance = MagicBoxApplySku.create({
                    'MBSid': str(uuid.uuid1()),
                    'MBAid': mba.MBAid,
                    'SKUid': skuid,
                    'SKUprice': skuprice,
                    'MBSstock': mbsstock,
                    'HighestPrice': highestprice,
                    'LowestPrice': lowestprice
                })
                instance_list.append(mbs_instance)
            db.session.add_all(instance_list)
        super(CMagicBox, self).create_approval('tomagicbox', sup.SUid, mbaid, ApplyFrom.supplizer.value)
        return Success('修改成功', {'mbaid': mbaid})

    def shelf_award(self):
        """撤销申请"""
        if is_supplizer():
            sup = Supplizer.query.filter_by_(SUid=request.user.id).first_("账号状态错误")
        else:
            raise AuthorityError()
        data = parameter_required(('mbaid',))
        mbaid = data.get('mbaid')
        with db.auto_commit():
            apply_info = MagicBoxApply.query.filter(MagicBoxApply.MBAid == mbaid,
                                                    MagicBoxApply.isdelete == False,
                                                    MagicBoxApply.MBAstatus == ApplyStatus.wait_check.value,
                                                    ).first_('只有待审核状态下的申请可以撤销')
            if apply_info.SUid != sup.SUid:
                raise AuthorityError("只能撤销属于自己的申请")
            apply_info.update({'MBAstatus': ApplyStatus.cancle.value})
            db.session.add(apply_info)
            # 返回库存
            product = Products.query.filter_by(PRid=apply_info.PRid, isdelete=False).first_('商品信息出错')
            gps_old = MagicBoxApplySku.query.filter(MagicBoxApplySku.MBAid == apply_info.MBAid,
                                                    MagicBoxApplySku.isdelete == False,
                                                    ).all()
            for sku in gps_old:
                sku_instance = ProductSku.query.filter_by(isdelete=False, PRid=product.PRid,
                                                          SKUid=sku.SKUid).first_('商品sku信息不存在')
                super(CMagicBox, self)._update_stock(int(sku.MBSstock), product, sku_instance)

            # 同时取消正在进行的审批流
            Approval.query.filter_by(AVcontent=apply_info.MBAid, AVstartid=sup.SUid,
                                     isdelete=False, AVstatus=ApplyStatus.wait_check.value
                                     ).update({'AVstatus': ApplyStatus.cancle.value})
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
            if sup and apply_info.SUid != sup.SUid:
                raise ParamsError('只能删除自己提交的申请')
            if apply_info.MBAstatus not in [ApplyStatus.cancle.value, ApplyStatus.reject.value,
                                           ApplyStatus.shelves.value]:
                raise StatusError('只能删除已下架、已拒绝、已撤销状态下的申请')
            apply_info.isdelete = True
            MagicBoxApplySku.query.filter_by_(MBAid=apply_info.MBAid).delete_()
            if is_admin():
                BASEADMIN().create_action(AdminActionS.delete.value, 'MagicBoxApply', mbaid)
        return Success('删除成功', {'mbaid': mbaid})

    def shelves(self):
        """下架申请"""
        if is_supplizer():
            usid = request.user.id
            sup = Supplizer.query.filter_by_(SUid=usid).first_('供应商信息错误')
            current_app.logger.info('Supplizer {} shelf magicbox apply'.format(sup.SUname))
        elif is_admin():
            usid = request.user.id
            admin = Admin.query.filter_by_(ADid=usid).first_('管理员信息错误')
            current_app.logger.info('Admin {} shelf magicbox apply'.format(admin.ADname))
            sup = None
        else:
            raise AuthorityError()
        data = parameter_required(('mbaid',))
        mbaid = data.get('mbaid')
        pending_box = MagicBoxJoin.query.filter(MagicBoxJoin.isdelete == False,
                                                MagicBoxJoin.MBJstatus == MagicBoxJoinStatus.pending.value,
                                                MagicBoxJoin.MBSendtime >= datetime.now().date(),
                                                MagicBoxJoin.MBAid == mbaid).first()
        if pending_box:
            current_app.logger.info('仍存在未完成礼盒 MBJid: {}'.format(pending_box.MBJid))
            raise StatusError('该商品仍有正在分享中的礼盒未完成，暂不能下架')

        with db.auto_commit():
            apply_info = MagicBoxApply.query.filter_by_(MBAid=mbaid).first_('无此申请记录')
            if sup and apply_info.SUid != usid:
                raise StatusError('只能下架自己的申请')
            if apply_info.MBAstatus != ApplyStatus.agree.value:
                raise StatusError('只能下架已通过的申请')
            apply_info.MBAstatus = ApplyStatus.shelves.value
            if is_admin():
                BASEADMIN().create_action(AdminActionS.update.value, 'MagicBoxApply', mbaid)
            # 返回库存
            product = Products.query.filter_by(PRid=apply_info.PRid, isdelete=False).first_('商品信息出错')
            mbs_old = MagicBoxApplySku.query.filter(MagicBoxApplySku.MBAid == apply_info.MBAid,
                                                    MagicBoxApplySku.isdelete == False,
                                                    ).all()
            for sku in mbs_old:
                sku_instance = ProductSku.query.filter_by(isdelete=False, PRid=product.PRid,
                                                          SKUid=sku.SKUid).first_('商品sku信息不存在')
                super(CMagicBox, self)._update_stock(int(sku.MBSstock), product, sku_instance)
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

    def _check_gear_price(self, gear_list):
        if not isinstance(gear_list, list):
            raise ParamsError('参数{}错误, 请按格式传递参数: 如 ["10-20", "15-30"]'.format(gear_list))
        for item in gear_list:
            tmp = list(map(lambda x: self._check_isint(x), item.split('-')))  # 校验每一项是否是整数
            try:
                if tmp[0] >= tmp[1] or tmp[0] == tmp[1] == 0:
                    raise ParamsError('每档随机变化金额中填写的第二个数字需大于第一个数字')
            except IndexError:
                raise ParamsError('请按格式合理传递参数: 如 ["10-20", "15-30"]')
        return json.dumps(gear_list)

    @staticmethod
    def _check_isint(num):
        if not num.isdigit():
            raise ParamsError('参数“{}”错误，仅可填写整数'.format(num))
        return int(num)

    @staticmethod
    def _check_price(price):
        if not re.match(r'(^[1-9](\d+)?(\.\d{1,2})?$)|(^0$)|(^\d\.\d{1,2}$)', str(price)) or float(price) < 0:
            raise ParamsError("数字'{}'错误， 只能输入大于0的数字".format(price))
        return Decimal(price).quantize(Decimal('0.00'))

    @staticmethod
    def _check_stock(stock):
        if not str(stock).isdigit() or int(stock) <= 0:
            raise ParamsError("库存'{}'错误， 只能输入大于0的整数".format(stock))
        return int(stock)
