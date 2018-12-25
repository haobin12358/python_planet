# -*- coding: utf-8 -*-
import json
import uuid
from datetime import datetime
from decimal import Decimal
from flask import request, current_app
from planet.common.error_response import ParamsError, SystemError
from planet.common.params_validates import parameter_required
from planet.common.success_response import Success
from planet.common.token_handler import is_tourist, admin_required, token_required
from planet.config.enums import TrialCommodityStatus, ActivityType, Client, OrderFrom, PayType
from planet.control.COrder import COrder
from planet.extensions.register_ext import db
from planet.models import TrialCommodity, TrialCommodityImage, User, TrialCommoditySku, ProductBrand, Activity, \
    UserAddress, AddressArea, AddressCity, AddressProvince, OrderPart, OrderMain, OrderPay, TrialCommoditySkuValue


class CTrialCommodity(COrder):

    def get_commodity_list(self):
        if not is_tourist():
            usid = request.user.id
            user = self._verify_user(usid)
            current_app.logger.info('get commodity list, User is {}'.format(user.USname))
            tourist = 0
        else:
            tourist = 1
        args = parameter_required(('page_num', 'page_size'))
        tcstatus = args.get('tcstatus', 'upper')
        if str(tcstatus) not in ['upper', 'off_shelves', 'auditing', 'all']:
            raise ParamsError('tcstatus, 参数错误')
        tcstatus = getattr(TrialCommodityStatus, tcstatus).value
        commodity_list = TrialCommodity.query.filter_(TrialCommodity.isdelete == False,
                                                      TrialCommodity.TCstatus == tcstatus,
                                                      TrialCommodity.AgreeStartTime <= datetime.now(),
                                                      TrialCommodity.AgreeEndTime >= datetime.now()
                                                      ).all_with_page()
        for commodity in commodity_list:
            commodity.fields = ['TCid', 'TCtitle', 'TCdescription', 'TCdeposit', 'TCmainpic']
            # mouth = round(commodity.TCdeadline / 31)
            # 押金天数处理
            # deadline = commodity.TCdeadline
            # remainder_day = deadline % 31
            # day_deadline = '{}天'.format(remainder_day) if remainder_day > 0 else ''
            # remainder_mouth = deadline // 31
            # mouth_deadline = '{}个月'.format(remainder_mouth) if remainder_mouth > 0 else ''
            # commodity.fill('zh_remarks', mouth_deadline + day_deadline + "{}元".format(int(commodity.TCdeposit)))
            commodity.fill("zh_remarks", "{0}天{1}元".format(commodity.TCdeadline, int(commodity.TCdeposit)))
        background = Activity.query.filter_by_(ACtype=ActivityType.free_use.value, ACshow=True).first()
        banner = background["ACtopPic"] if background else ""
        remarks = getattr(background, "ACdesc", "体验专区") if background else "体验专区"
        data = {
            "banner": banner,
            "remarks": remarks,
            "commodity": commodity_list
            }
        return Success(data=data).get_body(tourist=tourist)

    def get_commodity(self):
        if not is_tourist():
            usid = request.user.id
            user = self._verify_user(usid)
            current_app.logger.info('get commodity details, User is {}'.format(user.USname))
            tourist = 0
        else:
            tourist = 1
        args = parameter_required(('tcid',))
        tcid = args.get('tcid')
        commodity = TrialCommodity.query.filter_(TrialCommodity.TCid == tcid, TrialCommodity.isdelete == False
                                                 ).first_('未找到商品信息, tcid参数异常')
        commodity.TCattribute = json.loads(getattr(commodity, 'TCattribute') or '[]')
        commodity.TCstatus = TrialCommodityStatus(commodity.TCstatus).zh_value
        # 品牌
        brand = ProductBrand.query.filter_by_(PBid=commodity.PBid, isdelete=False).first()
        brand.hide('PBlinks', 'PBbackgroud')
        commodity.fill('brand', brand)
        # 商品图片
        image_list = TrialCommodityImage.query.filter_by_(TCid=tcid, isdelete=False).all()
        [image.hide('TCid') for image in image_list]
        commodity.fill('image', image_list)
        # 押金天数处理
        # deadline = commodity.TCdeadline
        # remainder_day = deadline % 31
        # day_deadline = '{}天'.format(remainder_day) if remainder_day > 0 else ''
        # remainder_mouth = deadline // 31
        # mouth_deadline = '{}个月'.format(remainder_mouth) if remainder_mouth > 0 else ''
        # commodity.fill('zh_deadline', mouth_deadline + day_deadline)
        commodity.fill('zh_deadline', '{}天'.format(commodity.TCdeadline))
        # 填充sku
        skus = TrialCommoditySku.query.filter_by_(TCid=tcid).all()
        sku_value_item = []
        for sku in skus:
            sku.SKUattriteDetail = json.loads(getattr(sku, 'SKUattriteDetail') or '[]')
            sku.SKUprice = commodity.TCdeposit
            sku_value_item.append(sku.SKUattriteDetail)
        commodity.fill('skus', skus)
        # 拼装skuvalue
        sku_value_instance = TrialCommoditySkuValue.query.filter_by_(TCid=tcid).first()
        if not sku_value_instance:
            sku_value_item_reverse = []
            for index, name in enumerate(commodity.TCattribute):
                value = list(set([attribute[index] for attribute in sku_value_item]))
                value = sorted(value)
                combination = {
                    'name': name,
                    'value': value
                }
                sku_value_item_reverse.append(combination)
        else:
            sku_value_item_reverse = []
            tskuvalue = json.loads(sku_value_instance.TSKUvalue)
            for index, value in enumerate(tskuvalue):
                sku_value_item_reverse.append({
                    'name': commodity.TCattribute[index],
                    'value': value
                })

        commodity.fill('skuvalue', sku_value_item_reverse)
        return Success(data=commodity).get_body(tourist=tourist)

    @admin_required
    def add_commodity(self):
        """添加试用商品"""
        data = parameter_required(('tctitle', 'tcdescription', 'tcdeposit', 'tcdeadline', 'tcfreight',
                                   'tcmainpic', 'tcattribute', 'tcdesc', 'pbid', 'images', 'skus',
                                   'tskuvalue', 'applystarttime', 'applyendtime'
                                   ))
        tcid = str(uuid.uuid1())
        tcattribute = data.get('tcattribute')
        tcdescription = data.get('tcdescription')
        tcdesc = data.get('tcdesc')
        tcdeposit = data.get('tcdeposit')
        # tcstocks = data.get('tcstocks')
        tcstocks = 0
        pbid = data.get('pbid')
        images = data.get('images')
        skus = data.get('skus')
        if not isinstance(images, list) or not isinstance(skus, list):
            raise ParamsError('images/skus, 参数错误')
        ProductBrand.query.filter_by_(PBid=pbid).first_('pbid 参数错误, 未找到相应品牌')
        with db.auto_commit():
            session_list = []

            for image in images:
                parameter_required(('tcipic', 'tcisort'), datafrom=image)
                image_info = TrialCommodityImage.create({
                    'TCIid': str(uuid.uuid1()),
                    'TCid': tcid,
                    'TCIpic': image.get('tcipic'),
                    'TCIsort': image.get('tcisort')
                })
                session_list.append(image_info)
            # sku
            sku_detail_list = []  # 一个临时的列表, 使用记录的sku_detail来检测sku_value是否符合规范
            for sku in skus:
                parameter_required(('skupic', 'skustock', 'skuattritedetail'), datafrom=sku)
                skuattritedetail = sku.get('skuattritedetail')
                if not isinstance(skuattritedetail, list) or len(skuattritedetail) != len(tcattribute):
                    raise ParamsError('skuattritedetail与tcattribute不符')
                sku_detail_list.append(skuattritedetail)
                skustock = sku.get('skustock')

                # assert int(skustock) <= int(tcstocks), 'skustock参数错误，单sku库存大于库存总数'
                tcstocks += int(skustock)  # 计算总库存
                sku_info = TrialCommoditySku.create({
                    'SKUid': str(uuid.uuid1()),
                    'TCid': tcid,
                    'SKUpic': sku.get('skupic'),
                    'SKUprice': tcdeposit,
                    'SKUstock': int(skustock),
                    'SKUattriteDetail': json.dumps(skuattritedetail)
                })
                session_list.append(sku_info)
            # skuvalue
            tskuvalue = data.get('tskuvalue')
            if tskuvalue:
                if not isinstance(tskuvalue, list) or len(tskuvalue) != len(tcattribute):
                    raise ParamsError('tskuvalue与prattribute不符')
                sku_reverce = []
                for index in range(len(tcattribute)):
                    value = list(set([attribute[index] for attribute in sku_detail_list]))
                    sku_reverce.append(value)
                    # 对应位置的列表元素应该相同
                    if set(value) != set(tskuvalue[index]):
                        raise ParamsError('请核对tskuvalue')
                # sku_value表
                sku_value_instance = TrialCommoditySkuValue.create({
                    'TSKUid': str(uuid.uuid1()),
                    'TCid': tcid,
                    'TSKUvalue': json.dumps(tskuvalue)
                })
                session_list.append(sku_value_instance)

            commodity = TrialCommodity.create({
                'TCid': tcid,
                'TCtitle': data.get('tctitle'),
                'TCdescription': tcdescription,
                'TCdeposit': tcdeposit,
                'TCdeadline': data.get('tcdeadline'),  # 暂时先按天为单位
                'TCfreight': data.get('tcfreight'),
                'TCstocks': tcstocks,
                'TCstatus': TrialCommodityStatus.auditing.value,
                'TCmainpic': data.get('tcmainpic'),
                'TCattribute': json.dumps(tcattribute or '[]'),
                'TCdesc': tcdesc or [],
                'TCremarks': data.get('tcremarks'),
                'CreaterId': request.user.id,
                'PBid': pbid,
                'ApplyStartTime': data.get('applystarttime'),
                'ApplyEndTime': data.get('applyendtime')
            })
            session_list.append(commodity)
            db.session.add_all(session_list)
        return Success("添加成功", {'tcid': tcid})

    @admin_required
    def update_commodity(self):
        """修改试用商品"""
        data = parameter_required(('tcid', 'tctitle', 'tcdescription', 'tcdeposit', 'tcdeadline', 'tcfreight',
                                   'tcmainpic', 'tcattribute', 'tcdesc', 'pbid', 'images', 'skus',
                                   'tskuvalue', 'applystarttime', 'applyendtime'
                                   ))
        tcattribute = data.get('tcattribute')
        tcdescription = data.get('tcdescription')
        tcdesc = data.get('tcdesc')
        tcdeposit = data.get('tcdeposit')
        tcstocks = 0
        pbid = data.get('pbid')
        images = data.get('images')
        skus = data.get('skus')
        tskuvalue = data.get('tskuvalue')
        tcid = data.get('tcid')
        commodity = TrialCommodity.query.filter_by_(TCid=tcid).first_('未找到该试用商品信息')  # todo 审核中或拒绝能否修改
        if not isinstance(images, list) or not isinstance(skus, list):
            raise ParamsError('images/skus, 参数错误')
        ProductBrand.query.filter_by_(PBid=pbid).first_('pbid 参数错误, 未找到相应品牌')
        with db.auto_commit():
            session_list = []
            if images:
                old_tciids = list()
                [old_tciids.append(id.TCIid) for id in TrialCommodityImage.query.filter_by_(TCid=tcid).all()]
                current_app.logger.info("Exist old tciids is {}".format(old_tciids))
                for image in images:
                    if 'tciid' in image:
                        tciid = image.get('tciid')
                        old_tciids.remove(tciid)

                    else:
                        new_tciid = str(uuid.uuid1())
                        new_img_instance = TrialCommodityImage.create({
                            'TCIid': new_tciid,
                            'TCid': tcid,
                            'TCIpic': image.get('tcipic'),
                            'TCIsort': image.get('tcisort')
                        })
                        session_list.append(new_img_instance)
                current_app.logger.info("Delete old exist tciids is {}".format(old_tciids))
                [TrialCommodityImage.query.filter_by_(TCIid=old_tciid).delete_() for old_tciid in old_tciids]
            if skus:
                sku_detail_list = list()  # 一个临时的列表, 使用记录的sku_detail来检测sku_value是否符合规范
                for sku in skus:
                    parameter_required(('skupic', 'skustock', 'skuattritedetail'), datafrom=sku)
                    skuattritedetail = sku.get('skuattritedetail')
                    if not isinstance(skuattritedetail, list) or len(skuattritedetail) != len(tcattribute):
                        raise ParamsError('skuattritedetail与tcattribute不符')
                    sku_detail_list.append(skuattritedetail)
                    skustock = sku.get('skustock')
                    skus_list = list()
                    if 'skuid' in sku:
                        skuid = sku.get('skuid')
                        skus_list.append(skuid)
                        sku_instance = TrialCommoditySku.query.filter_by({'SKUid': skuid}).first_('sku不存在')
                        sku_instance.update({
                            'TCid': tcid,
                            'SKUpic': sku.get('skupic'),
                            'SKUattriteDetail': json.dumps(skuattritedetail),
                            'SKUstock': int(skustock),
                            'SKUprice': tcdeposit
                        })
                        session_list.append(sku_instance)
                    else:
                        new_sku_instance = TrialCommoditySku.create({
                            'SKUid': str(uuid.uuid1()),
                            'TCid': tcid,
                            'SKUpic': sku.get('skupic'),
                            'SKUprice': tcdeposit,
                            'SKUstock': int(skustock),
                            'SKUattriteDetail': json.dumps(skuattritedetail)
                        })
                        session_list.append(new_sku_instance)
                    tcstocks += int(skustock)  # 计算总库存

                    # 剩下的就是删除
                    TrialCommoditySku.query.filter(TrialCommoditySku.isdelete == False,
                                                   TrialCommoditySku.TCid == tcid,
                                                   TrialCommoditySku.SKUid.notin_(skus_list)
                                                   ).delete_(synchronize_session=False)
            if tskuvalue:
                # todo 与sku校验
                if not isinstance(tskuvalue, list) or len(tskuvalue) != len(tcattribute):
                    raise ParamsError('tskuvalue与prattribute不符')
                exists_skuvalue = TrialCommoditySkuValue.query.filter_by_(TCid=tcid).first()
                if exists_skuvalue:
                    exists_skuvalue.update({
                        'TSKUvalue': json.dumps(tskuvalue)
                    })
                    session_list.append(exists_skuvalue)
                else:
                    new_sku_value_instance = TrialCommoditySkuValue.create({
                        'TSKUid': str(uuid.uuid1()),
                        'TCid': tcid,
                        'TSKUvalue': json.dumps(tskuvalue)
                    })
                    session_list.append(new_sku_value_instance)
            else:
                TrialCommoditySkuValue.query.filter_by_(TCid=tcid).delete_()  # 如果不传就删除原来的

            upinfo = commodity.update(
                {
                    'TCtitle': data.get('tctitle'),
                    'TCdescription': tcdescription,
                    'TCdeposit': tcdeposit,
                    'TCdeadline': data.get('tcdeadline'),  # 暂时先按天为单位
                    'TCfreight': data.get('tcfreight'),
                    'TCstocks': tcstocks,
                    'TCstatus': TrialCommodityStatus.auditing.value,
                    'TCmainpic': data.get('tcmainpic'),
                    'TCattribute': json.dumps(tcattribute or '[]'),
                    'TCdesc': tcdesc or [],
                    'TCremarks': data.get('tcremarks'),
                    'CreaterId': request.user.id,
                    'PBid': pbid,
                    'ApplyStartTime': data.get('applystarttime'),
                    'ApplyEndTime': data.get('applyendtime')
                })
            session_list.append(upinfo)
            db.session.add_all(session_list)

    @admin_required
    def del_commodity(self):
        """删除试用商品"""
        data = parameter_required(("tcid",))
        tcid = data.get('tcid')
        TrialCommodity.query.filter_by_(TCid=tcid).first_('未找到商品信息, tcid参数异常')
        with db.auto_commit():
            TrialCommodity.query.filter_by(TCid=tcid).delete_()
            TrialCommodityImage.query.filter_by(TCid=tcid).delete_()
            TrialCommoditySku.query.filter_by(TCid=tcid).delete_()
            TrialCommoditySkuValue.query.filter_by(TCid=tcid).delete_()
        return Success('删除成功', {'tcid': tcid})

    @token_required
    def create_order(self):
        data = parameter_required(('tcid', 'pbid', 'skuid', 'omclient', 'uaid', 'opaytype'))
        usid = request.user.id
        user = self._verify_user(usid)
        current_app.logger.info('User {} is buying a trialcommodity'.format(user.USname))
        uaid = data.get('uaid')
        tcid = data.get('tcid')
        opaytype = data.get('opaytype')  # 支付方式
        try:
            omclient = int(data.get('omclient', Client.wechat.value))  # 下单设备
            Client(omclient)
        except Exception:
            raise ParamsError('客户端来源错误')
        with db.auto_commit():
            # 用户的地址信息
            user_address_instance = db.session.query(UserAddress).filter_by_({'UAid': uaid, 'USid': usid}).first_('地址信息不存在')
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
            opayno = self.wx_pay.nonce_str
            model_bean = []

            omid = str(uuid.uuid1())
            pbid = data.get('pbid')
            ommessage = data.get('ommessage')
            product_brand_instance = db.session.query(ProductBrand).filter_by_({'PBid': pbid}).first_('品牌id: {}不存在'.format(pbid))

            opid = str(uuid.uuid1())
            skuid = data.get('skuid')
            opnum = int(data.get('nums', 1))
            assert opnum > 0, 'nums <= 0, 参数错误'
            sku_instance = db.session.query(TrialCommoditySku).filter_by_({'SKUid': skuid}).first_('skuid: {}不存在'.format(skuid))
            if sku_instance.TCid != tcid:
                raise ParamsError('skuid 与 tcid, 商品不对应')
            assert int(sku_instance.SKUstock) - int(opnum) >= 0, '商品库存不足'
            product_instance = db.session.query(TrialCommodity).filter_by_({'TCid': tcid}).first_('skuid: {}对应的商品不存在'.format(skuid))
            if product_instance.PBid != pbid:
                raise ParamsError('品牌id: {}与skuid: {}不对应'.format(pbid, skuid))
            small_total = Decimal(str(product_instance.TCdeposit)) * opnum
            order_part_dict = {
                'OMid': omid,
                'OPid': opid,
                'PRid': product_instance.TCid,
                'SKUid': skuid,
                'PRattribute': product_instance.TCattribute,
                'SKUattriteDetail': sku_instance.SKUattriteDetail,
                'PRtitle': product_instance.TCtitle,
                'SKUprice': sku_instance.SKUprice,
                'PRmainpic': product_instance.TCmainpic,
                'OPnum': opnum,
                'OPsubTotal': small_total,
                'UPperid': user.USid,
                # 'UPperid2': user.USid,
            }
            order_part_instance = OrderPart.create(order_part_dict)
            model_bean.append(order_part_instance)

            # 对应商品销量 + num sku库存 -num
            db.session.query(TrialCommodity).filter_by_(TCid=tcid).update({
                'TCsalesValue': TrialCommodity.TCsalesValue + opnum, 'TCstocks': TrialCommodity.TCstocks - opnum
            })
            db.session.query(TrialCommoditySku).filter_by_(SKUid=skuid).update({
                'SKUstock': TrialCommoditySku.SKUstock - opnum
            })
            # 主单
            order_main_dict = {
                'OMid': omid,
                'OMno': self._generic_omno(),
                'OPayno': opayno,
                'USid': usid,
                'OMfrom': OrderFrom.trial_commodity.value,
                'PBname': product_brand_instance.PBname,
                'PBid': pbid,
                'OMclient': omclient,
                'OMfreight': 0,  # 运费暂时为0 / product_instance.TCfreight
                'OMmount': small_total,
                'OMmessage': ommessage,
                'OMtrueMount': small_total,
                # 收货信息
                'OMrecvPhone': omrecvphone,
                'OMrecvName': omrecvname,
                'OMrecvAddress': omrecvaddress,

                'UseCoupon': False  # 试用商品不能使用优惠券
            }
            order_main_instance = OrderMain.create(order_main_dict)
            model_bean.append(order_main_instance)

            # 支付数据表
            order_pay_dict = {
                'OPayid': str(uuid.uuid4()),
                'OPayno': opayno,
                'OPayType': opaytype,
                'OPayMount': small_total,
            }
            order_pay_instance = OrderPay.create(order_pay_dict)
            model_bean.append(order_pay_instance)
            db.session.add_all(model_bean)
        # 生成支付信息
        body = product_instance.TCtitle
        pay_args = self._pay_detail(omclient, opaytype, opayno, float(small_total), body, openid=user.USopenid1 or user.USopenid2)
        response = {
            'pay_type': PayType(opaytype).name,
            'opaytype': opaytype,
            'args': pay_args
        }
        return Success('创建成功', data=response)

    @staticmethod
    def _verify_user(usid):
        return User.query.filter_by_(USid=usid).first_('用户信息不存在')

