import datetime
import json
import uuid
import re
from decimal import Decimal

from flask import request, current_app
from sqlalchemy import cast, Date, func

from planet.common.error_response import AuthorityError, ParamsError, StatusError
from planet.common.params_validates import parameter_required
from planet.common.success_response import Success
from planet.common.token_handler import is_supplizer, is_admin, common_user, is_tourist, token_required
from planet.config.enums import ApplyFrom, ApplyStatus, ProductStatus, Client, OrderFrom, PayType, AdminActionS, \
    ProductFrom, ProductBrandStatus, ActivityType, GuessGroupStatus, GuessRecordStatus, GuessRecordDigits, \
    OrderMainStatus
from planet.control.BaseControl import BASEAPPROVAL, BASEADMIN
from planet.control.COrder import COrder
from planet.extensions.register_ext import db
from planet.models import Admin, Supplizer, GroupGoodsProduct, Products, ProductSku, GroupGoodsSku, ProductBrand, \
    ProductImage, Approval, User, OrderPay, OrderMain, UserAddress, AddressArea, AddressCity, AddressProvince, \
    OrderPart, GuessGroup, GuessRecord, Activity


class CGuessGroup(COrder, BASEAPPROVAL):

    def apply(self):
        """申请添加商品"""
        if is_supplizer():
            sup = Supplizer.query.filter_by_(SUid=request.user.id).first_("账号状态错误")
        else:
            raise AuthorityError("请使用相应品牌")
        data = parameter_required(('prid', 'skus', 'gpday'))
        prid, skus, gpday = data.get('prid'), data.get('skus'), data.get('gpday')
        if not isinstance(gpday, list):
            raise ParamsError('gpday格式错误')

        instance_list, gpid_list = [], []
        with db.auto_commit():
            product = Products.query.outerjoin(ProductBrand, ProductBrand.PBid == Products.PBid
                                               ).filter(Products.PRid == prid,
                                                        Products.isdelete == False,
                                                        Products.PRstatus == ProductStatus.usual.value,
                                                        Products.PRfrom == ProductFrom.supplizer.value,
                                                        Products.CreaterId == sup.SUid,
                                                        ProductBrand.isdelete == False,
                                                        ProductBrand.PBstatus == ProductBrand.PBstatus == ProductBrandStatus.upper.value,
                                                        ProductBrand.SUid == sup.SUid).first_('只能选择自己品牌下的商品')

            for day in gpday:
                if datetime.datetime.strptime(day, '%Y-%m-%d').date() < datetime.datetime.now().date():
                    raise ParamsError('不允许申请当前时间之前的日期')
                exist_apply = GroupGoodsProduct.query.filter(GroupGoodsProduct.PRid == prid,
                                                             GroupGoodsProduct.isdelete == False,
                                                             GroupGoodsProduct.SUid == sup.SUid,
                                                             GroupGoodsProduct.GPday == day).first()
                if exist_apply:
                    raise ParamsError('您已添加过该商品{}日的申请'.format(day))
                ggp_instance = GroupGoodsProduct.create({
                    'GPid': str(uuid.uuid1()),
                    'SUid': sup.SUid,
                    'PRid': prid,
                    'GPfreight': 0,  # 运费暂默认为0
                    'GPstatus': ApplyStatus.wait_check.value,
                    'GPday': day,
                })
                instance_list.append(ggp_instance)
                gpid_list.append(ggp_instance.GPid)
                for sku in skus:
                    parameter_required(('skuid', 'gsstock', 'skuprice', 'skufirstlevelprice',
                                        'skusecondlevelprice', 'skuthirdlevelprice'), datafrom=sku)
                    skuid, skuprice, gsstock = sku.get('skuid'), sku.get('skuprice'), sku.get('gsstock')
                    skufirstlevelprice = sku.get('skufirstlevelprice')
                    skusecondlevelprice = sku.get('skusecondlevelprice')
                    skuthirdlevelprice = sku.get('skuthirdlevelprice')
                    skuprice, skufirstlevelprice, skusecondlevelprice, skuthirdlevelprice = list(
                        map(lambda x: self._check_price(x),
                            (skuprice, skufirstlevelprice, skusecondlevelprice, skuthirdlevelprice)))
                    if not (skuprice >= skufirstlevelprice >= skusecondlevelprice >= skuthirdlevelprice):
                        raise ParamsError('请合理设置猜中数字后的价格')
                    gsstock = self._check_stock(gsstock)
                    sku_instance = ProductSku.query.filter_by(isdelete=False, PRid=product.PRid,
                                                              SKUid=skuid).first_('商品sku信息不存在')
                    # 从商品sku中减库存
                    super(CGuessGroup, self)._update_stock(-gsstock, product, sku_instance)

                    ggsku_instance = GroupGoodsSku.create({
                        'GSid': str(uuid.uuid1()),
                        'GPid': ggp_instance.GPid,
                        'SKUid': skuid,
                        'GSstock': gsstock,
                        'SKUPrice': skuprice,
                        'SKUFirstLevelPrice': skufirstlevelprice,
                        'SKUSecondLevelPrice': skusecondlevelprice,
                        'SKUThirdLevelPrice': skuthirdlevelprice,
                    })
                    instance_list.append(ggsku_instance)

                    # 库存单
                    # outstock_instance = OutStock.create({'OSid': osid,
                    #                                      'SKUid': skuid,
                    #                                      'OSnum': gsstock
                    #                                      })

            db.session.add_all(instance_list)
        for gpid in gpid_list:  # 添加审批流
            super(CGuessGroup, self).create_approval('togroupgoods', sup.SUid, gpid, applyfrom=ApplyFrom.supplizer.value)
        return Success('申请成功', data=dict(GPid=gpid_list))

    def update(self):
        """修改"""
        if is_supplizer():
            sup = Supplizer.query.filter_by_(SUid=request.user.id).first_("账号状态错误")
        else:
            raise AuthorityError('仅可编辑自己提交的申请')
        data = parameter_required(('gpid', 'skus'))
        gpid, skus = data.get('gpid'), data.get('skus')
        gp = GroupGoodsProduct.query.filter(GroupGoodsProduct.isdelete == False,
                                            GroupGoodsProduct.GPid == gpid,
                                            GroupGoodsProduct.SUid == sup.SUid,
                                            GroupGoodsProduct.GPstatus.in_([ApplyStatus.cancle.value,
                                                                            ApplyStatus.reject.value,
                                                                            ApplyStatus.shelves.value])
                                            ).first_("当前状态不可进行编辑")
        product = Products.query.filter(Products.PRid == gp.PRid,
                                        Products.isdelete == False,
                                        Products.PRstatus == ProductStatus.usual.value,
                                        Products.CreaterId == sup.SUid,
                                        ).first_("当前商品状态不允许编辑")
        instance_list = []
        with db.auto_commit():
            gp.update({'GPstatus': ApplyStatus.wait_check.value})
            instance_list.append(gp)

            # 原sku全部删除
            old_ips = GroupGoodsSku.query.filter_by_(GPid=gp.GPid).all()
            for old_ipsku in old_ips:
                old_ipsku.isdelete = True
            # 接收新sku并重新扣除库存
            for sku in skus:
                parameter_required(('skuid', 'gsstock', 'skuprice', 'skufirstlevelprice',
                                    'skusecondlevelprice', 'skuthirdlevelprice'), datafrom=sku)
                skuid, skuprice, gsstock = sku.get('skuid'), sku.get('skuprice'), sku.get('gsstock')
                skufirstlevelprice = sku.get('skufirstlevelprice')
                skusecondlevelprice = sku.get('skusecondlevelprice')
                skuthirdlevelprice = sku.get('skuthirdlevelprice')
                skuprice, skufirstlevelprice, skusecondlevelprice, skuthirdlevelprice = list(
                    map(lambda x: self._check_price(x),
                        (skuprice, skufirstlevelprice, skusecondlevelprice, skuthirdlevelprice)))
                if not (skuprice >= skufirstlevelprice >= skusecondlevelprice >= skuthirdlevelprice):
                    raise ParamsError('请合理设置猜中数字后的价格')
                gsstock = self._check_stock(gsstock)
                sku_instance = ProductSku.query.filter_by(isdelete=False, PRid=gp.PRid,
                                                          SKUid=skuid).first_('商品sku信息不存在')

                # 从商品sku中减库存
                super(CGuessGroup, self)._update_stock(-gsstock, product, sku_instance)
                ggsku_instance = GroupGoodsSku.create({
                    'GSid': str(uuid.uuid1()),
                    'GPid': gp.GPid,
                    'SKUid': skuid,
                    'GSstock': gsstock,
                    'SKUPrice': skuprice,
                    'SKUFirstLevelPrice': skufirstlevelprice,
                    'SKUSecondLevelPrice': skusecondlevelprice,
                    'SKUThirdLevelPrice': skuthirdlevelprice,
                })
                instance_list.append(ggsku_instance)
            db.session.add_all(instance_list)
        super(CGuessGroup, self).create_approval('togroupgoods', sup.SUid, gpid, applyfrom=ApplyFrom.supplizer.value)
        return Success('更新成功', {'gpid': gp.GPid})

    def get(self):
        """商品详情"""
        args = request.args.to_dict()
        gpid, ggid, gg = args.get('gpid'), args.get('ggid'), None
        if not gpid and not ggid:
            raise ParamsError('gpid | ggid 至少需要其一')
        if ggid:
            gg = GuessGroup.query.filter(GuessGroup.isdelete == False, GuessGroup.GGid == ggid,
                                         # GuessGroup.GGendtime >= datetime.datetime.now()
                                         ).first_('该拼团已结束')
            gpid = gg.GPid
        filter_args = [GroupGoodsProduct.isdelete == False, GroupGoodsProduct.GPid == gpid]
        if common_user() or is_tourist():
            filter_args.append(GroupGoodsProduct.GPstatus == ApplyStatus.agree.value)
        gp = GroupGoodsProduct.query.filter(*filter_args).first_("没有找到该商品")
        product = self._fill_gp(gp, gg)
        return Success('获取成功', data=product)

    def _fill_gp(self, gp, gg=None):
        product = Products.query.filter(Products.PRid == gp.PRid, Products.isdelete == False).first_('商品已下架')
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
        gps_list = GroupGoodsSku.query.filter_by(GPid=gp.GPid, isdelete=False).all()
        gpsku_price = []
        skus = []
        sku_value_item = []
        for gps in gps_list:
            gpsku_price.append(round(float(gps.SKUPrice), 2))
            sku = ProductSku.query.filter_by(SKUid=gps.SKUid, isdelete=False).first()
            if not sku:
                current_app.logger.info('该sku已删除 skuid = {0}'.format(gps.SKUid))
                continue
            sku.hide('SKUstock', 'SkudevideRate', 'PRid')
            sku.fill('skuprice', gps.SKUPrice)
            sku.fill('gsstock', gps.GSstock)
            sku.fill('gsid', gps.GSid)

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
        product.fill('skuvalue', sku_value_item_reverse)
        product.fill('gpstatus_zh', ApplyStatus(gp.GPstatus).zh_value)
        product.fill('gpstatus_en', ApplyStatus(gp.GPstatus).name)
        product.fill('gpstatus', gp.GPstatus)
        product.fill('gpdeposit', max(gpsku_price))  # 显示的押金
        product.fill('gprejectreason', gp.GPrejectReason)
        product.fill('gpid', gp.GPid)
        product.fill('gpday', gp.GPday)
        product.fill('gpfreight', gp.GPfreight)  # 运费目前默认为0
        # if not gg:
        #     gg_query = GuessGroup.query.filter(GuessGroup.isdelete == False,
        #                                        GuessGroup.GPid == gp.GPid,
        #                                        GuessGroup.GGendtime >= datetime.datetime.now(),
        #                                        GuessGroup.GGstatus == GuessGroupStatus.pending.value)
        #     if common_user():
        #         gg_query = gg_query.outerjoin(GuessRecord, GuessRecord.GGid == GuessGroup.GGid
        #                                       ).filter(GuessRecord.isdelete == False,
        #                                                GuessRecord.USid == request.user.id,
        #                                                GuessRecord.GRstatus == GuessRecordStatus.valid.value)
        #     gg = gg_query.first()

        if common_user() or is_tourist():
            headers, numbers = self._fill_number_and_headers(gg)
            status = getattr(gg, 'GGstatus', None)
            ggstatus_zh = GuessGroupStatus(status).zh_value if isinstance(status, int) else None
            tradeprice = None
            if gg and status == GuessGroupStatus.completed.value:
                tradeprice = db.session.query(OrderMain.OMtrueMount).outerjoin(
                    GuessRecord, GuessRecord.OMid == OrderMain.OMid
                ).filter(OrderMain.isdelete == False, GuessRecord.isdelete == False, GuessRecord.GGid == gg.GGid,
                         OrderMain.USid == request.user.id, GuessRecord.GRstatus == GuessRecordStatus.valid.value,
                         ).scalar() if common_user() else None
                ggstatus_zh = '本期正确结果: {}'.format(gg.GGcorrectNum) if common_user() else ggstatus_zh

            guess_group = {'ggid': getattr(gg, 'GGid', None),
                           'ggstatus': status,
                           'ggstatus_en': GuessGroupStatus(status).name if isinstance(status, int) else None,
                           'ggstatus_zh': ggstatus_zh,
                           'headers': headers,
                           'numbers': numbers,
                           'tradeprice': tradeprice,
                           'rules': db.session.query(Activity.ACdesc
                                                     ).filter_by_(ACtype=ActivityType.guess_group.value).scalar()
                           }
            product.fill('guess_group', guess_group)
            have_paid = self.verify_have_paid(gp, gg)
            usid = request.user.id if common_user() else None
            joined = self._already_joined(gg, usid)
            if gg and gg.GGstatus != GuessGroupStatus.pending.value:
                have_paid = True
                joined = True
            product.fill('topaydeposit', bool(not have_paid))
            product.fill('joined', bool(joined))
        return product

    @staticmethod
    def verify_have_paid(gp, gg=None):
        """检验该团/商品 是否已付过押金"""
        if not common_user():
            return
        usid = request.user.id
        om_list = []
        order_main = None
        if gg:
            order_main = OrderMain.query.join(
                GuessRecord, GuessRecord.OMid == OrderMain.OMid
            ).filter(GuessRecord.USid == usid, GuessRecord.isdelete == False,
                     GuessRecord.GRstatus == GuessRecordStatus.valid.value,
                     GuessRecord.GGid == gg.GGid,
                     OrderMain.isdelete == False,
                     OrderMain.OMinRefund == False,
                     OrderMain.OMfrom == OrderFrom.guess_group.value,
                     OrderMain.USid == usid,
                     OrderMain.OMstatus.notin_((OrderMainStatus.cancle.value,
                                                OrderMainStatus.wait_pay.value))
                     ).first()
            current_app.logger.info('have ggid return paid om is {}'.format(order_main))
        if not gg or not order_main:
            order_mains = OrderMain.query.outerjoin(OrderPart,
                                                    OrderPart.OMid == OrderMain.OMid
                                                    ).filter(OrderMain.isdelete == False,
                                                             OrderMain.OMinRefund == False,
                                                             OrderMain.OMstatus == OrderMainStatus.wait_send.value,
                                                             OrderMain.USid == usid,
                                                             OrderMain.OMfrom == OrderFrom.guess_group.value,
                                                             OrderPart.isdelete == False,
                                                             OrderPart.PRid == gp.GPid
                                                             ).all()
            for om in order_mains:
                gr = GuessRecord.query.outerjoin(GuessGroup,
                                                 GuessGroup.GGid == GuessRecord.GGid
                                                 ).filter(GuessRecord.isdelete == False,
                                                          GuessRecord.GRstatus == GuessRecordStatus.valid.value,
                                                          GuessRecord.OMid == om.OMid,
                                                          GuessGroup.isdelete == False,
                                                          GuessGroup.GGstatus != GuessGroupStatus.failed.value
                                                          ).first()
                if not gr:
                    om_list.append(om)

            current_app.logger.info('get paid order main {} ; id : {}'.format(len(order_mains),
                                                                              [i.OMid for i in order_mains]))
            order_main = om_list[0] if len(om_list) > 0 else None
            current_app.logger.info('filter paid om count: {}'.format(len(om_list)))
            current_app.logger.info('return paid om is {}'.format(order_main))
        return order_main

    @staticmethod
    def _fill_number_and_headers(gg=None):
        headers, numbers = [], []
        if not gg:
            return [None, None, None], [None, None, None]
        hundreddigits = GuessRecord.query.filter_by(isdelete=False, GGid=gg.GGid,
                                                    GRdigits=GuessRecordDigits.hundredDigits.value,
                                                    GRstatus=GuessRecordStatus.valid.value
                                                    ).first()
        headers.append(getattr(hundreddigits, 'UShead', None))
        numbers.append(getattr(hundreddigits, 'GRnumber', None))
        tendigits = GuessRecord.query.filter_by(isdelete=False, GGid=gg.GGid,
                                                GRdigits=GuessRecordDigits.tenDigits.value,
                                                GRstatus=GuessRecordStatus.valid.value
                                                ).first()
        headers.append(getattr(tendigits, 'UShead', None))
        numbers.append(getattr(tendigits, 'GRnumber', None))
        singledigits = GuessRecord.query.filter_by(isdelete=False, GGid=gg.GGid,
                                                   GRdigits=GuessRecordDigits.singleDigits.value,
                                                   GRstatus=GuessRecordStatus.valid.value
                                                   ).first()
        headers.append(getattr(singledigits, 'UShead', None))
        numbers.append(getattr(singledigits, 'GRnumber', None))
        return headers, numbers

    def _fill_single_group(self, gg):
        gg.hide('USid')
        gg.fill('ggstatus_en', GuessGroupStatus(getattr(gg, 'GGstatus', 0)).name)
        gg.fill('ggstatus_zh', GuessGroupStatus(getattr(gg, 'GGstatus', 0)).zh_value)
        headers, numbers = self._fill_number_and_headers(gg)
        gg.fill('headers', headers)
        gg.fill('numbers', numbers)
        if common_user():
            gr = GuessRecord.query.filter_by_(GGid=gg.GGid, USid=request.user.id,
                                              GRstatus=GuessRecordStatus.valid.value).first()
            if gr:
                type = '我参与的'
                if gg.USid == request.user.id:
                    type = '我发起的'
                gg.fill('type', type)

    def list(self):
        """拼团/商品列表"""
        args = request.args.to_dict()
        now = datetime.datetime.now()
        option = args.get('option')
        gpstatus = args.get('gpstatus')
        starttime, endtime = args.get('starttime', '2019-01-01') or '2019-01-01', args.get('endtime', '2100-01-01') or '2100-01-01'
        if is_admin() or is_supplizer():
            return self._back_group_product_list(gpstatus, starttime, endtime)

        if str(option) == 'my':
            my_group = []
            if common_user():
                my_group = self._filter_joined_group().all_with_page()
            list(map(lambda x: self._fill_single_group(x), my_group))
            return Success(data=my_group)

        elif str(option) == 'all':
            all_group = self._filter_not_joined_group().all_with_page()
            list(map(lambda x: self._fill_single_group(x), all_group))
            return Success(data=all_group)

        my_group = []
        if common_user():
            my_group = self._filter_joined_group().distinct().limit(2).all()

        list(map(lambda x: self._fill_single_group(x), my_group))

        all_group = self._filter_not_joined_group().distinct().limit(2).all()

        list(map(lambda x: self._fill_single_group(x), all_group))

        group_goods = GroupGoodsProduct.query.filter(GroupGoodsProduct.isdelete == False,
                                                     GroupGoodsProduct.GPstatus == ApplyStatus.agree.value,
                                                     GroupGoodsProduct.GPday == now.date()
                                                     ).order_by(GroupGoodsProduct.createtime.desc()).all_with_page()
        for gp in group_goods:
            gp.hide('SUid', 'PRid', 'GPfreight')
            product = Products.query.filter(Products.PRid == gp.PRid, Products.isdelete == False).first()
            if not product:
                continue
            gps_list = GroupGoodsSku.query.filter_by(GPid=gp.GPid, isdelete=False).all()
            gpsku_price = [gps.SKUPrice for gps in gps_list]
            gp.fill('gpstatus_en', ApplyStatus(gp.GPstatus).name)
            gp.fill('gpstatus_zh', ApplyStatus(gp.GPstatus).zh_value)
            gp.fill('prmainpic', product['PRmainpic'])
            gp.fill('prtitle', product.PRtitle)
            gp.fill('gpdeposit', max(gpsku_price))

        res = {'my_group': my_group,
               'all_group': all_group,
               'group_goods': group_goods
               }

        return Success(data=res)

    @staticmethod
    def _filter_joined_group():
        usid = request.user.id
        my_joined = GuessGroup.query.outerjoin(GuessRecord, GuessRecord.GGid == GuessGroup.GGid
                                               ).filter(GuessGroup.isdelete == False,
                                                        GuessRecord.isdelete == False,
                                                        GuessRecord.USid == usid,
                                                        # GuessRecord.GRstatus == GuessRecordStatus.valid.value,
                                                        # GuessGroup.GGendtime >= now,
                                                        # GuessGroup.GGstatus.in_((GuessGroupStatus.pending.value,
                                                        #                          GuessGroupStatus.waiting.value)),
                                                        ).order_by(func.field(GuessGroup.GGstatus, 0, 10, 20, -10),
                                                                   GuessGroup.createtime.desc())
        return my_joined

    @staticmethod
    def _filter_not_joined_group():
        filter_args = []
        if common_user():  # 只筛选自己没参加过的团
            usid = request.user.id
            all_gr = db.session.query(GuessRecord.GGid, func.group_concat(GuessRecord.USid)
                                      ).filter(GuessRecord.isdelete == False,
                                               GuessRecord.GRstatus == GuessRecordStatus.valid.value
                                               ).group_by(GuessRecord.GGid).all()
            ggid_list = [gr[0] for gr in all_gr if usid not in gr[1]]
            filter_args.append(GuessGroup.GGid.in_(ggid_list))

        all_group = GuessGroup.query.filter(GuessGroup.isdelete == False,
                                            GuessGroup.GGendtime >= datetime.datetime.now(),
                                            GuessGroup.GGstatus.in_((GuessGroupStatus.pending.value,
                                                                     GuessGroupStatus.waiting.value)),
                                            * filter_args
                                            ).order_by(func.field(GuessGroup.GGstatus, 0, 10, 20, -10),
                                                       GuessGroup.createtime.desc())
        return all_group

    def _back_group_product_list(self, gpstatus, starttime, endtime):
        filter_args = []
        try:
            gpstatus = getattr(ApplyStatus, gpstatus).value
        except Exception:
            gpstatus = None
        if gpstatus:
            filter_args.append(GroupGoodsProduct.GPstatus == gpstatus)

        if is_supplizer():
            filter_args.append(GroupGoodsProduct.SUid == request.user.id)

        group_goods = GroupGoodsProduct.query.filter(GroupGoodsProduct.isdelete == False,
                                                     GroupGoodsProduct.GPday >= starttime,
                                                     GroupGoodsProduct.GPday <= endtime,
                                                     *filter_args
                                                     ).order_by(GroupGoodsProduct.createtime.desc()).all_with_page()
        for gp in group_goods:
            gp.hide('SUid', 'GPfreight')
            product = Products.query.filter(Products.PRid == gp.PRid, Products.isdelete == False).first()
            pbname = db.session.query(ProductBrand.PBname).filter_by_(isdelete=False, PBid=product.PBid).scalar()
            gp.fill('pbname', pbname)
            if not product:
                continue
            gps_list = GroupGoodsSku.query.filter_by(GPid=gp.GPid, isdelete=False).all()
            for gps in gps_list:
                product_sku = ProductSku.query.filter_by(SKUid=gps.SKUid, isdelete=False).first()
                if not product_sku:
                    continue
                gps.fill('skuattritedetail', json.loads(getattr(product_sku, 'SKUattriteDetail', '')))
            gp.fill('skus', gps_list)
            gp.fill('gpstatus_en', ApplyStatus(gp.GPstatus).name)
            gp.fill('gpstatus_zh', ApplyStatus(gp.GPstatus).zh_value)
            gp.fill('prmainpic', product['PRmainpic'])
            gp.fill('prtitle', product.PRtitle)
        return Success(data=group_goods)

    @staticmethod
    def _already_joined(gg=None, usid=None):
        if not gg or not usid:
            return
        return GuessRecord.query.filter_by(isdelete=False, USid=usid,
                                           GGid=gg.GGid,
                                           GRstatus=GuessRecordStatus.valid.value).first()

    @token_required
    def join(self):
        """参加拼团"""
        user = User.query.filter(User.isdelete == False, User.USid == request.user.id).first_('请重新登录')
        data = parameter_required(('gpid', 'number', 'digits'))
        ggid, gpid, number, digits = data.get('ggid', None), data.get('gpid'), data.get('number'), data.get('digits')
        now = datetime.datetime.now()
        if now.hour >= 21:
            raise StatusError('每日21:00后停止竞猜，等待开奖中')
        if not re.match(r'^[0-9]$', str(number)):
            raise ParamsError('数字格式错误')
        try:
            GuessRecordDigits(digits)
        except Exception:
            raise ParamsError('参数 digits 错误')
        session_list = []
        with db.auto_commit():
            gg = None
            if ggid:
                gg = GuessGroup.query.filter(GuessGroup.isdelete == False,
                                             GuessGroup.GGid == ggid,
                                             GuessGroup.GGstatus == GuessGroupStatus.pending.value,
                                             GuessGroup.GGendtime >= now
                                             ).first()
                gpid = gg.GPid
            gp = GroupGoodsProduct.query.filter(GroupGoodsProduct.isdelete == False,
                                                GroupGoodsProduct.GPstatus == ApplyStatus.agree.value,
                                                GroupGoodsProduct.GPid == gpid
                                                ).first_('商品已下架')
            product = Products.query.filter(Products.isdelete == False, Products.PRid == gp.PRid).first()

            order_main = self.verify_have_paid(gp)
            if not order_main:
                raise StatusError('进行竞猜前，请先选择相应商品规格支付押金')

            if not ggid:
                gps_list = GroupGoodsSku.query.filter_by(GPid=gp.GPid, isdelete=False).all()
                gpsku_price = [gps.SKUPrice for gps in gps_list]

                day = now.date() + datetime.timedelta(days=1)
                while GroupGoodsProduct.query.filter(GroupGoodsProduct.isdelete == False,
                                                     GroupGoodsProduct.PRid == gp.PRid,
                                                     GroupGoodsProduct.GPstatus == ApplyStatus.agree.value,
                                                     GroupGoodsProduct.GPday == day
                                                     ).first():
                    day = day + datetime.timedelta(days=1)

                endtime = day - datetime.timedelta(days=1)
                endtime = endtime.strftime('%Y%m%d') + '210000'
                endtime = datetime.datetime.strptime(endtime, '%Y%m%d%H%M%S')

                group_instance = GuessGroup.create({'GGid': str(uuid.uuid1()),
                                                    'USid': user.USid,
                                                    'GPid': gp.GPid,
                                                    'PRtitle': product.PRtitle,
                                                    'PRmainpic': product.PRmainpic,
                                                    'GPdeposit': max(gpsku_price),
                                                    'GGstarttime': now,
                                                    'GGendtime': endtime,
                                                    'GGstatus': GuessGroupStatus.pending.value
                                                    })
                session_list.append(group_instance)
                message = '发起拼团成功'
            else:
                group_instance = gg
                message = '参与拼团成功'
            if self._already_joined(group_instance, user.USid):
                raise StatusError('您已参与过该团竞猜')
            if GuessRecord.query.filter_by(isdelete=False, GRdigits=digits,
                                           GGid=group_instance.GGid,
                                           GRstatus=GuessRecordStatus.valid.value
                                           ).first():
                raise StatusError('{}数已有人竞猜，请选择其余位置'.format(GuessRecordDigits(digits).zh_value))
            record_instance = GuessRecord.create({'GRid': str(uuid.uuid1()),
                                                  'GGid': group_instance.GGid,
                                                  'GPid': gp.GPid,
                                                  'GRnumber': number,
                                                  'GRdigits': digits,
                                                  'USid': user.USid,
                                                  'UShead': user.USheader,
                                                  'USname': user.USname,
                                                  'OMid': order_main.OMid,
                                                  'GRstatus': GuessRecordStatus.valid.value
                                                  })
            session_list.append(record_instance)
            db.session.add_all(session_list)
            db.session.flush()

            record_count = GuessRecord.query.filter_by(isdelete=False,
                                                       GGid=group_instance.GGid,
                                                       GRstatus=GuessRecordStatus.valid.value
                                                       ).count()

            if record_count == 3:  # 拼团三位数填满后更改状态
                group_instance.update({'GGstatus': GuessGroupStatus.waiting.value})
                db.session.add(group_instance)

        return Success(message=message, data={'ggid': group_instance.GGid, 'grnumber': number, 'grdigits': digits})

    def cancel_apply(self):
        """取消申请"""
        if is_supplizer():
            sup = Supplizer.query.filter_by_(SUid=request.user.id).first_("账号状态错误")
        else:
            raise AuthorityError()
        data = parameter_required(('gpid',))
        with db.auto_commit():
            gp = GroupGoodsProduct.query.filter(GroupGoodsProduct.GPid == data.get('gpid'),
                                                GroupGoodsProduct.isdelete == False,
                                                GroupGoodsProduct.GPstatus == ApplyStatus.wait_check.value
                                                ).first_("只有待审核状态下的申请可以撤销")
            if gp.SUid != sup.SUid:
                raise AuthorityError("只能撤销属于自己的申请")
            gp.update({'GPstatus': ApplyStatus.cancle.value})
            db.session.add(gp)
            # 返回库存
            product = Products.query.filter_by(PRid=gp.PRid, isdelete=False).first_('商品信息出错')
            gps_old = GroupGoodsSku.query.filter(GroupGoodsSku.GPid == gp.GPid,
                                                 GroupGoodsSku.isdelete == False,
                                                 ).all()
            for sku in gps_old:
                sku_instance = ProductSku.query.filter_by(isdelete=False, PRid=product.PRid,
                                                          SKUid=sku.SKUid).first_('商品sku信息不存在')
                super(CGuessGroup, self)._update_stock(int(sku.GSstock), product, sku_instance)

            # 同时取消正在进行的审批流
            Approval.query.filter_by(AVcontent=gp.GPid, AVstartid=sup.SUid,
                                     isdelete=False, AVstatus=ApplyStatus.wait_check.value
                                     ).update({'AVstatus': ApplyStatus.cancle.value})
        return Success('已取消申请', {'gpid': gp.GPid})

    def delete(self):
        """删除申请"""
        if is_supplizer():
            usid = request.user.id
            sup = Supplizer.query.filter_by_(SUid=usid).first_('供应商信息错误')
            current_app.logger.info('Supplizer {} delete guess group apply'.format(sup.SUname))
        elif is_admin():
            usid = request.user.id
            admin = Admin.query.filter_by_(ADid=usid).first_('管理员信息错误')
            current_app.logger.info('Admin {} delete guess group apply'.format(admin.ADname))
            sup = None
        else:
            raise AuthorityError()
        data = parameter_required(('gpid',))
        gpid = data.get('gpid')
        with db.auto_commit():
            apply_info = GroupGoodsProduct.query.filter_by(GPid=gpid, isdelete=False).first_('没有该商品记录')
            if sup and apply_info.SUid != sup.SUid:
                raise ParamsError('只能删除自己提交的申请')
            if apply_info.GPstatus not in [ApplyStatus.cancle.value, ApplyStatus.reject.value,
                                           ApplyStatus.shelves.value]:
                raise StatusError('只能删除已下架、已拒绝、已撤销状态下的申请')
            apply_info.isdelete = True
            GroupGoodsSku.query.filter(GroupGoodsSku.GPid == apply_info.GPid).delete_()
            if is_admin():
                BASEADMIN().create_action(AdminActionS.delete.value, 'GroupGoodsProduct', apply_info.GPid)
        return Success('删除成功', {'gpid': gpid})

    def shelf(self):
        """下架"""
        if is_supplizer():
            usid = request.user.id
            sup = Supplizer.query.filter_by_(SUid=usid).first_('供应商信息错误')
            current_app.logger.info('Supplizer {} shelf guess group apply'.format(sup.SUname))
        elif is_admin():
            usid = request.user.id
            admin = Admin.query.filter_by_(ADid=usid).first_('管理员信息错误')
            current_app.logger.info('Admin {} shelf guess group apply'.format(admin.ADname))
            sup = None
        else:
            raise AuthorityError()
        data = parameter_required(('gpid',))
        gpid = data.get('gpid')
        pending_group = GuessGroup.query.filter(GuessGroup.isdelete == False,
                                                GuessGroup.GGstatus.in_((GuessGroupStatus.pending.value,
                                                                         GuessGroupStatus.waiting.value)),
                                                GuessGroup.GGendtime >= datetime.datetime.now(),
                                                GuessGroup.GPid == gpid).first()
        if pending_group:
            raise StatusError('该商品仍有拼团未完成，暂不能下架')
        with db.auto_commit():
            gp = GroupGoodsProduct.query.filter_by_(GPid=gpid).first_('无此申请记录')
            if sup and gp.SUid != usid:
                raise StatusError('只能下架自己的商品')
            if gp.GPstatus != ApplyStatus.agree.value:
                raise StatusError('只能下架已上架的商品')
            gp.GPstatus = ApplyStatus.shelves.value
            if is_admin():
                BASEADMIN().create_action(AdminActionS.update.value, 'GroupGoodsProduct', gpid)
            # 返回库存
            product = Products.query.filter_by(PRid=gp.PRid, isdelete=False).first_('商品信息出错')
            gps_old = GroupGoodsSku.query.filter(GroupGoodsSku.GPid == gp.GPid,
                                                 GroupGoodsSku.isdelete == False,
                                                 ).all()
            for sku in gps_old:
                sku_instance = ProductSku.query.filter_by(isdelete=False, PRid=product.PRid,
                                                          SKUid=sku.SKUid).first_('商品sku信息不存在')
                super(CGuessGroup, self)._update_stock(int(sku.GSstock), product, sku_instance)
        return Success('下架成功', {'gpid': gpid})

    @token_required
    def order(self):
        """下单"""
        data = parameter_required(('gpid', 'pbid', 'gsid', 'omclient', 'uaid'))
        usid = request.user.id
        user = User.query.filter_by_(USid=usid).first_("请重新登录")
        current_app.logger.info('User {} is buying a guess group Product'.format(user.USname))
        uaid = data.get('uaid')
        gpid = data.get('gpid')
        opaytype = data.get('opaytype', 0)  # 支付方式
        if datetime.datetime.now().hour >= 21:
            raise StatusError(' ^_^  正在等待今日开奖 (每日21:00后停止竞猜，请明日再来)')
        try:
            omclient = int(data.get('omclient', Client.wechat.value))  # 下单设备
            Client(omclient)
        except Exception:
            raise ParamsError('客户端来源错误')
        with db.auto_commit():
            # 用户的地址信息
            user_address_instance = db.session.query(UserAddress).filter_by_({'UAid': uaid, 'USid': usid}).first_(
                '地址信息不存在')
            omrecvphone = user_address_instance.UAphone
            areaid = user_address_instance.AAid
            # 地址拼接
            area, city, province = db.session.query(AddressArea, AddressCity, AddressProvince).filter(
                AddressArea.ACid == AddressCity.ACid, AddressCity.APid == AddressProvince.APid).filter(
                AddressArea.AAid == areaid).first_('地址有误')
            address = getattr(province, "APname", '') + getattr(city, "ACname", '') + getattr(area, "AAname", '')
            omrecvaddress = address + user_address_instance.UAtext
            omrecvname = user_address_instance.UAname
            opayno = self.wx_pay.nonce_str
            model_bean = []

            omid = str(uuid.uuid1())
            pbid = data.get('pbid')
            ommessage = data.get('ommessage')
            product_brand_instance = ProductBrand.query.filter_by_(PBid=pbid,
                                                                   PBstatus=ProductBrandStatus.upper.value
                                                                   ).first_('该品牌已下架')

            opid = str(uuid.uuid1())
            gsid = data.get('gsid')
            opnum = int(data.get('nums', 1))
            opnum = 1  # 购买数量暂时只支持一件
            # assert opnum > 0, 'nums <= 0, 参数错误'
            sku_instance = GroupGoodsSku.query.filter_by_(GSid=gsid).first_('gsid: {} 不存在'.format(gsid))
            product_sku = ProductSku.query.filter_by_(SKUid=sku_instance.SKUid).first_("商品sku不存在")
            if sku_instance.GPid != gpid:
                raise ParamsError('gsid 与 gpid 商品不对应')
            if int(sku_instance.GSstock) - int(opnum) < 0:
                raise StatusError('商品库存不足')
            group_product = GroupGoodsProduct.query.filter(GroupGoodsProduct.GPid == gpid,
                                                           GroupGoodsProduct.isdelete == False,
                                                           GroupGoodsProduct.GPstatus == ApplyStatus.agree.value,
                                                           ).first_("该拼团商品已下架")
            if self.verify_have_paid(group_product):
                raise StatusError('您已付过该商品押金，可直接参与该商品的拼团')
            product_instance = Products.query.filter(Products.isdelete == False,
                                                     Products.PRid == group_product.PRid,
                                                     Products.PRstatus == ProductStatus.usual.value
                                                     ).first_("该商品已下架")
            if product_instance.PBid != pbid:
                raise ParamsError('品牌id {} 与商品id {} 不对应'.format(pbid, gsid))
            small_total = Decimal(sku_instance.SKUPrice) * Decimal(opnum)
            order_part_dict = {
                'OMid': omid,
                'OPid': opid,
                'PRid': group_product.GPid,  # 是拼团商品id，不是原商品
                'SKUid': gsid,  # 拼团商品的gsid
                'PRattribute': product_instance.PRattribute,
                'SKUattriteDetail': product_sku.SKUattriteDetail,
                'PRtitle': product_instance.PRtitle,
                'SKUprice': sku_instance.SKUPrice,
                'PRmainpic': product_instance.PRmainpic,
                'OPnum': opnum,
                'OPsubTotal': small_total,
                'PRfrom': product_instance.PRfrom,
            }
            order_part_instance = OrderPart.create(order_part_dict)
            model_bean.append(order_part_instance)

            # 对应商品销量 + num sku库存 -num
            db.session.query(Products).filter_by_(PRid=group_product.PRid
                                                  ).update({'PRsalesValue': Products.PRsalesValue + opnum})
            db.session.query(GroupGoodsSku).filter_by_(GSid=gsid
                                                       ).update({'GSstock': GroupGoodsSku.GSstock - opnum})

            # 主单
            order_main_dict = {
                'OMid': omid,
                'OMno': self._generic_omno(),
                'OPayno': opayno,
                'USid': usid,
                'OMfrom': OrderFrom.guess_group.value,
                'PBname': product_brand_instance.PBname,
                'PBid': product_brand_instance.PBid,
                'OMclient': omclient,
                'OMfreight': 0,  # 运费暂时为0
                'OMmount': small_total,
                'OMmessage': ommessage,
                'OMtrueMount': small_total,
                # 收货信息
                'OMrecvPhone': omrecvphone,
                'OMrecvName': omrecvname,
                'OMrecvAddress': omrecvaddress,
                'PRcreateId': product_instance.CreaterId,
                'UseCoupon': False
            }
            order_main_instance = OrderMain.create(order_main_dict)
            model_bean.append(order_main_instance)

            # 支付数据表
            order_pay_dict = {
                'OPayid': str(uuid.uuid1()),
                'OPayno': opayno,
                'OPayType': PayType.wechat_pay.value,
                'OPayMount': small_total,
            }
            order_pay_instance = OrderPay.create(order_pay_dict)
            model_bean.append(order_pay_instance)
            db.session.add_all(model_bean)
        from planet.extensions.tasks import auto_cancle_order
        auto_cancle_order.apply_async(args=([omid],), countdown=30 * 60, expires=40 * 60, )
        # 生成支付信息
        body = product_instance.PRtitle
        pay_args = self._pay_detail(omclient, opaytype, opayno, round(float(small_total), 2), body,
                                    openid=user.USopenid2 or user.USopenid1)
        response = {
            'pay_type': PayType(opaytype).name,
            'opaytype': opaytype,
            'omid': omid,
            'omtruemount': small_total,
            'args': pay_args
        }
        return Success('创建成功', data=response)

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





