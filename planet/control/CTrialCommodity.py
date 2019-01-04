# -*- coding: utf-8 -*-
import json
import uuid
from datetime import datetime
from decimal import Decimal
from flask import request, current_app
from sqlalchemy import or_, and_

from planet.common.error_response import ParamsError, AuthorityError, StatusError
from planet.common.params_validates import parameter_required
from planet.common.success_response import Success
from planet.common.token_handler import is_tourist, admin_required, token_required, is_admin, is_supplizer
from planet.config.enums import TrialCommodityStatus, ActivityType, Client, OrderFrom, PayType, ApplyFrom, ApplyStatus
from planet.control.BaseControl import BASEAPPROVAL
from planet.control.COrder import COrder
from planet.extensions.register_ext import db
from planet.models import TrialCommodity, TrialCommodityImage, User, TrialCommoditySku, ProductBrand, Activity, \
    UserAddress, AddressArea, AddressCity, AddressProvince, OrderPart, OrderMain, OrderPay, TrialCommoditySkuValue, \
    Admin, Supplizer, Approval


class CTrialCommodity(COrder, BASEAPPROVAL):

    def get_commodity_list(self):
        if is_tourist():
            usid = None
            tourist = 1
            time_filter = (TrialCommodity.AgreeStartTime <= datetime.now(),
                           TrialCommodity.AgreeEndTime >= datetime.now())
        elif is_admin():
            usid = request.user.id
            admin = self._check_admin(usid)
            current_app.logger.info('Admin {0} get commodity list'.format(admin.ADname))
            tourist = 'admin'
            time_filter = tuple()
        elif is_supplizer():
            usid = request.user.id
            sup = self._check_supplizer(usid)
            current_app.logger.info('Supplizer {} get commodity list'.format(sup.SUname))
            time_filter = (TrialCommodity.CreaterId == usid,)
            tourist = 'supplizer'
        else:
            usid = request.user.id
            user = self._verify_user(usid)
            current_app.logger.info('User {0} get commodity list'.format(user.USname))
            tourist = 0
            time_filter = (TrialCommodity.AgreeStartTime <= datetime.now(),
                           TrialCommodity.AgreeEndTime >= datetime.now())

        args = parameter_required(('page_num', 'page_size'))
        kw = args.get('kw', '').split() or ['']
        tcstatus = args.get('tcstatus', 'upper')
        if str(tcstatus) not in ['upper', 'auditing', 'reject', 'cancel', 'sell_out', 'all']:
            raise ParamsError('tcstatus, 参数错误')
        tcstatus = getattr(TrialCommodityStatus, tcstatus).value
        commodity_list = TrialCommodity.query.filter_(or_(and_(*[TrialCommodity.TCtitle.contains(x) for x in kw]),
                                                          and_(*[ProductBrand.PBname.contains(x) for x in kw]),
                                                          ),
                                                      TrialCommodity.isdelete == False,
                                                      TrialCommodity.TCstatus == tcstatus,
                                                      *time_filter).order_by(TrialCommodity.createtime.desc()).all_with_page()
        for commodity in commodity_list:
            commodity.hide('TCrejectReason')
            if commodity.TCstatus == TrialCommodityStatus.reject.value:
                reason = commodity.TCrejectReason or '不符合审核规定，请修改后重新提交'
                commodity.fill("reject_reason", reason)
            commodity.fill("zh_remarks", "{0}天{1}元".format(commodity.TCdeadline, commodity.TCdeposit))
            prbrand = ProductBrand.query.filter_by_(PBid=commodity.PBid).first()
            commodity.fill('brand', prbrand)
            commodity.TCattribute = json.loads(commodity.TCattribute)
            commodity.fill('zh_tcstatus', TrialCommodityStatus(commodity.TCstatus).zh_value)
            commodity.hide('CreaterId', 'PBid')
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
        if is_tourist():
            usid = None
            tourist = 1
        elif is_admin():
            usid = request.user.id
            admin = self._check_admin(usid)
            current_app.logger.info('Admin {} get commodity details'.format(admin.ADname))
            tourist = 'admin'
        elif is_supplizer():
            usid = request.user.id
            sup = self._check_supplizer(usid)
            current_app.logger.info('Supplizer {} get commodity details'.format(sup.SUname))
            tourist = 'supplizer'
        else:
            usid = request.user.id
            user = self._verify_user(usid)
            current_app.logger.info('User {} get commodity details'.format(user.USname))
            tourist = 0
        args = parameter_required(('tcid',))
        tcid = args.get('tcid')
        commodity = TrialCommodity.query.filter_(TrialCommodity.TCid == tcid, TrialCommodity.isdelete == False
                                                 ).first_('未找到商品信息, tcid参数异常')
        commodity.TCattribute = json.loads(getattr(commodity, 'TCattribute') or '[]')
        commodity.TCstatus = TrialCommodityStatus(commodity.TCstatus).zh_value
        # 品牌
        brand = ProductBrand.query.filter_by_(PBid=commodity.PBid, isdelete=False).first()
        if brand:
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

    def add_commodity(self):
        """添加试用商品"""
        if is_supplizer():
            usid = request.user.id
            sup = self._check_supplizer(usid)
            current_app.logger.info('Supplizer {} creat commodity'.format(sup.SUname))
            tcfrom = ApplyFrom.supplizer.value
        elif is_admin():
            usid = request.user.id
            admin = self._check_admin(usid)
            current_app.logger.info('Admin {} creat commodity'.format(admin.ADname))
            tcfrom = ApplyFrom.platform.value
        else:
            raise AuthorityError()
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
                'TCfrom': tcfrom,
                'ApplyStartTime': data.get('applystarttime'),
                'ApplyEndTime': data.get('applyendtime')
            })
            session_list.append(commodity)
            db.session.add_all(session_list)
            # 添加进审批流
            super().create_approval('totrialcommodity', request.user.id, tcid, tcfrom)
        return Success("添加成功", {'tcid': tcid})

    def update_commodity(self):
        """修改试用商品"""
        if is_supplizer():
            usid = request.user.id
            sup = self._check_supplizer(usid)
            current_app.logger.info('Supplizer {} update commodity'.format(sup.SUname))
        elif is_admin():
            usid = request.user.id
            admin = self._check_admin(usid)
            current_app.logger.info('Admin {} update commodity'.format(admin.ADname))
            sup = None
        else:
            raise AuthorityError()
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
        commodity = TrialCommodity.query.filter_by_(TCid=tcid).first_('未找到该试用商品信息')
        if sup:
            assert commodity.CreaterId == usid, '供应商只能修改自己上传的商品'
        if not isinstance(images, list) or not isinstance(skus, list):
            raise ParamsError('images/skus, 参数错误')
        ProductBrand.query.filter_by_(PBid=pbid).first_('未找到该品牌信息')
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
                    # 'TCstatus': TrialCommodityStatus.auditing.value,  # 修改时状态暂不做更改，重新添加个单独提交的接口
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
        return Success('修改成功', {'tcid': tcid})

    def cancel_commodity_apply(self):
        """撤销自己的申请"""
        if is_supplizer():
            usid = request.user.id
            sup = self._check_supplizer(usid)
            current_app.logger.info('Supplizer {} cancel commodity'.format(sup.SUname))
        elif is_admin():
            usid = request.user.id
            admin = self._check_admin(usid)
            current_app.logger.info('Admin {} cancel commodity'.format(admin.ADname))
        else:
            raise AuthorityError()
        data = parameter_required(('tcid',))
        tcid = data.get('tcid')
        with db.auto_commit():
            commodity = TrialCommodity.query.filter_by_(TCid=tcid).first_('无此商品信息')
            if commodity.TCstatus != TrialCommodityStatus.auditing.value:
                raise StatusError('只有在审核状态的申请可以撤销')
            if commodity.CreaterId != request.user.id:
                raise AuthorityError('仅可撤销自己提交的申请')
            commodity.TCstatus = TrialCommodityStatus.cancel.value
            # 同时将正在进行的审批流改为取消
            approval_info = Approval.query.filter_by_(AVcontent=tcid, AVstartid=request.user.id,
                                                      AVstatus=ApplyStatus.wait_check.value).first()
            approval_info.AVstatus = ApplyStatus.cancle.value
        return Success('取消成功', {'tcid': tcid})

    def shelves(self):
        """批量下架试用商品"""
        if is_supplizer():
            usid = request.user.id
            sup = self._check_supplizer(usid)
            current_app.logger.info('Supplizer {} shelves commodity'.format(sup.SUname))
        elif is_admin():
            usid = request.user.id
            admin = self._check_admin(usid)
            current_app.logger.info('Admin {} shelves commodity'.format(admin.ADname))
            sup = None
        else:
            raise AuthorityError()
        data = parameter_required(("tcids",))
        tcid_list = data.get('tcids')
        for tcid in tcid_list:
            commodity = TrialCommodity.query.filter_by_(TCid=tcid).first_('未找到商品信息, tcid参数异常')
            if sup:
                assert commodity.CreaterId == usid, '供应商只能下架自己上传的商品'
            if commodity.TCstatus != TrialCommodityStatus.upper.value:
                raise StatusError('只能下架正在上架状态的商品')
            with db.auto_commit():
                commodity.TCstatus = TrialCommodityStatus.reject.value
        return Success('下架成功', {'tcid': tcid_list})

    def resubmit_apply(self):
        """重新提交申请"""
        if is_supplizer():
            usid = request.user.id
            sup = self._check_supplizer(usid)
            current_app.logger.info('Supplizer {} resubmit commodity'.format(sup.SUname))
            nefrom = ApplyFrom.supplizer.value
        elif is_admin():
            usid = request.user.id
            admin = self._check_admin(usid)
            current_app.logger.info('Admin {} resubmit commodity'.format(admin.ADname))
            nefrom = ApplyFrom.platform.value
            sup = None
        else:
            raise AuthorityError()
        data = parameter_required(('tcid',))
        tcid = data.get('tcid')
        with db.auto_commit():
            commodity = TrialCommodity.query.filter_by_(TCid=tcid).first_('无此商品信息')
            if commodity.TCstatus not in [TrialCommodityStatus.cancel.value, TrialCommodityStatus.reject.value]:
                raise StatusError('只有撤销或已下架状态的申请可以重新提交')
            if sup:
                if commodity.CreaterId != usid:
                    raise AuthorityError('仅可重新提交自己上传的商品')
            commodity.TCstatus = TrialCommodityStatus.auditing.value
            # 重新创建一个审批流
            super().create_approval('totrialcommodity', usid, tcid, nefrom)
        return Success('提交成功', {'tcid': tcid})

    def del_commodity(self):
        """删除试用商品"""
        if is_supplizer():
            usid = request.user.id
            sup = self._check_supplizer(usid)
            current_app.logger.info('Supplizer {} delete commodity'.format(sup.SUname))
        elif is_admin():
            usid = request.user.id
            admin = self._check_admin(usid)
            current_app.logger.info('Admin {} delete commodity'.format(admin.ADname))
            sup = None
        else:
            raise AuthorityError()
        data = parameter_required(("tcid",))
        tcid = data.get('tcid')
        commodity = TrialCommodity.query.filter_by_(TCid=tcid).first_('未找到商品信息, tcid参数异常')
        if sup:
            assert commodity.CreaterId == usid, '供应商只能删除自己上传的商品'
        if commodity.TCstatus not in [TrialCommodityStatus.reject.value, TrialCommodityStatus.cancel.value]:
            raise StatusError('只能删除已下架或已撤销的商品')
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
            createdid = product_instance.CreaterId if product_instance.TCfrom == ApplyFrom.supplizer.value else None

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
                'PRcreateId': createdid,
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

    @staticmethod
    def _check_admin(usid):
        return Admin.query.filter_by_(ADid=usid).first_('管理员信息错误')

    @staticmethod
    def _check_supplizer(usid):
        return Supplizer.query.filter_by_(SUid=usid).first_('供应商信息错误')
