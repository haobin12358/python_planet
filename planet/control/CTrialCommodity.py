# -*- coding: utf-8 -*-
import json
import uuid
from flask import request, current_app

from planet.common.error_response import ParamsError
from planet.common.params_validates import parameter_required
from planet.common.success_response import Success
from planet.common.token_handler import is_tourist
from planet.config.enums import TrialCommodityStatus
from planet.extensions.register_ext import db
from planet.models import TrialCommodity, TrialCommodityImage, User, TrialCommoditySku


class CTrialCommodity(object):

    def get_commodity_list(self):
        if not is_tourist():
            usid = request.user.id
            user = self._verify_user(usid)
            current_app.logger.info('get commodity list user is {}'.format(user.USname))
            tourist = 0
        else:
            tourist = 1
        args = parameter_required(('page_num', 'page_size'))
        tcstatus = args.get('tcstatus', 'upper')
        if str(tcstatus) not in ['upper', 'off_shelves', 'all']:
            raise ParamsError('tcstatus, 参数错误')
        tcstatus = getattr(TrialCommodityStatus, tcstatus).value
        commodity_list = TrialCommodity.query.filter_(TrialCommodity.isdelete == False,
                                                      TrialCommodity.TCstatus == tcstatus
                                                      ).all_with_page()
        for commodity in commodity_list:
            commodity.fields = ['TCid', 'TCtitle', 'TCdescription', 'TCdeposit', 'TCmainpic']
            mouth = round(commodity.TCdeadline / 31)
            commodity.fill("zh_remarks", "{0}个月{1}元".format(mouth, int(commodity.TCdeposit)))
        banner = 'https://timgsa.baidu.com/timg?image&quality=80&size=b9999_10000&sec=1543320400194&di=e95f50d69a3cc07741c8ae9f7cc8f671&imgtype=0&src=http%3A%2F%2Fimgsrc.baidu.com%2Fimgad%2Fpic%2Fitem%2F7a899e510fb30f24cb158a3fc395d143ad4b037a.jpg'
        # todo 获取数据图片
        data = {
            "banner": banner,
            "remarks": '试用商品的一些话,试用商品的一些话,试用商品的一些话',
            "commodity": commodity_list
            }
        return Success(data=data).get_body(tourist=tourist)

    def get_commodity(self):
        if not is_tourist():
            usid = request.user.id
            user = self._verify_user(usid)
            current_app.logger.info('get commodity list user is {}'.format(user.USname))
            tourist = 0
        else:
            tourist = 1
        args = parameter_required(('tcid',))
        tcid = args.get('tcid')
        commodity = TrialCommodity.query.filter_(TrialCommodity.TCid == tcid, TrialCommodity.isdelete == False
                                                 ).first_('未找到商品信息, tcid参数异常')
        commodity.TCattribute = json.loads(getattr(commodity, 'TCattribute') or '[]')
        # 填充img
        image_list = TrialCommodityImage.query.filter_by_(TCid=tcid, isdelete=False).all()
        [image.hide('TCid') for image in image_list]
        commodity.fill('image', image_list)
        # 押金天数处理
        deadline = commodity.TCdeadline
        remainder_day = deadline % 31
        day_deadline = '{}天'.format(remainder_day) if remainder_day > 0 else ''
        mouth_deadline = '{}个月'.format(deadline // 31) + day_deadline
        commodity.fill('zh_deadline', mouth_deadline)
        # 填充sku
        skus = TrialCommoditySku.query.filter_by_(TCid=tcid).all()
        sku_value_item = []
        for sku in skus:
            sku.SKUattriteDetail = json.loads(getattr(sku, 'SKUattriteDetail') or '[]')
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

    @staticmethod
    def _verify_user(usid):
        return User.query.filter_by_(USid=usid).first_('用户信息不存在')

