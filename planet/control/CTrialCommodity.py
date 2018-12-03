# -*- coding: utf-8 -*-
import json
import uuid
from flask import request, current_app
from planet.common.error_response import ParamsError
from planet.common.params_validates import parameter_required
from planet.common.success_response import Success
from planet.common.token_handler import is_tourist, admin_required
from planet.config.enums import TrialCommodityStatus, ActivityType
from planet.extensions.register_ext import db
from planet.models import TrialCommodity, TrialCommodityImage, User, TrialCommoditySku, ProductBrand, Activity


class CTrialCommodity(object):

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
                                                      TrialCommodity.TCstatus == tcstatus
                                                      ).all_with_page()
        for commodity in commodity_list:
            commodity.fields = ['TCid', 'TCtitle', 'TCdescription', 'TCdeposit', 'TCmainpic']
            mouth = round(commodity.TCdeadline / 31)
            commodity.fill("zh_remarks", "{0}个月{1}元".format(mouth, int(commodity.TCdeposit)))
        background = Activity.query.filter_by_(ACtype=ActivityType.free_use.value).first()
        banner = background["ACtopPic"] if background else ""
        remarks = getattr(background, "ACdesc", "体验专区")
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
        deadline = commodity.TCdeadline
        remainder_day = deadline % 31
        day_deadline = '{}天'.format(remainder_day) if remainder_day > 0 else ''
        remainder_mouth = deadline // 31
        mouth_deadline = '{}个月'.format(remainder_mouth) if remainder_mouth > 0 else ''
        commodity.fill('zh_deadline', mouth_deadline + day_deadline)
        # 填充sku
        skus = TrialCommoditySku.query.filter_by_(TCid=tcid).all()
        sku_value_item = []
        for sku in skus:
            sku.SKUattriteDetail = json.loads(getattr(sku, 'SKUattriteDetail') or '[]')
            sku.SKUprice = commodity.TCdeposit
            sku_value_item.append(sku.SKUattriteDetail)
        commodity.fill('skus', skus)
        sku_value_item_reverse = []
        for index, name in enumerate(commodity.TCattribute):
            value = list(set([attribute[index] for attribute in sku_value_item]))
            value = sorted(value)
            combination = {
                'name': name,
                'value': value
            }
            sku_value_item_reverse.append(combination)
        commodity.fill('skuvalue', sku_value_item_reverse)
        return Success(data=commodity).get_body(tourist=tourist)

    @admin_required
    def add_commodity(self):
        data = parameter_required(('tctitle', 'tcdescription', 'tcdeposit', 'tcdeadline', 'tcfreight',
                                   'tcstocks', 'tcmainpic', 'tcattribute', 'tcdesc', 'pbid', 'images', 'skus'
                                   ))
        tcid = str(uuid.uuid1())
        tcattribute = data.get('tcattribute')
        tcdescription = data.get('tcdescription')
        tcdesc = data.get('tcdesc')
        tcdeposit = data.get('tcdeposit')
        tcstocks = data.get('tcstocks')
        pbid = data.get('pbid')
        images = data.get('images')
        skus = data.get('skus')
        if not isinstance(images, list) or not isinstance(skus, list):
            raise ParamsError('images/skus, 参数错误')
        ProductBrand.query.filter_by_(PBid=pbid).first_('pbid 参数错误, 未找到相应品牌')
        with db.auto_commit():
            session_list = []
            commodity = TrialCommodity.create({
                'TCid': tcid,
                'TCtitle': data.get('tctitle'),
                'TCdescription': tcdescription,
                'TCdeposit': tcdeposit,
                'TCdeadline': data.get('tcdeadline'),  # todo 暂不清楚后台设置单位是天还是月份
                'TCfreight': data.get('tcfreight'),
                'TCstocks': tcstocks,
                'TCstatus': TrialCommodityStatus.auditing.value,
                'TCmainpic': data.get('tcmainpic'),
                'TCattribute': json.dumps(tcattribute or '[]'),
                'TCdesc': json.dumps(tcdesc or '[]'),
                'TCremarks': data.get('tcremarks'),
                'CreaterId': request.user.id,
                'PBid': pbid,
            })
            session_list.append(commodity)
            for image in images:
                parameter_required(('tcipic', 'tcisort'), datafrom=image)
                image_info = TrialCommodityImage.create({
                    'TCIid': str(uuid.uuid1()),
                    'TCid': tcid,
                    'TCIpic': image.get('tcipic'),
                    'TCIsort': image.get('tcisort')
                })
                session_list.append(image_info)
            for sku in skus:
                parameter_required(('skupic', 'skustock', 'skuattritedetail'), datafrom=sku)
                skuattritedetail = sku.get('skuattritedetail')
                if not isinstance(skuattritedetail, list) or len(skuattritedetail) != len(tcattribute):
                    raise ParamsError('skuattritedetail与tcattribute不符')
                skustock = sku.get('skustock')
                assert int(skustock) <= int(tcstocks), 'skustock参数错误，单sku库存大于库存总数'
                sku_info = TrialCommoditySku.create({
                    'SKUid': str(uuid.uuid4()),
                    'TCid': tcid,
                    'SKUpic': sku.get('skupic'),
                    'SKUprice': tcdeposit,
                    'SKUstock': int(skustock),
                    'SKUattriteDetail': json.dumps(skuattritedetail)
                })
                session_list.append(sku_info)
            db.session.add_all(session_list)
        return Success("添加成功", {'tcid': tcid})











    @staticmethod
    def _verify_user(usid):
        return User.query.filter_by_(USid=usid).first_('用户信息不存在')

