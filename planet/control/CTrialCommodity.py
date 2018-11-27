# -*- coding: utf-8 -*-
import json
import uuid
from flask import request

from planet.common.error_response import ParamsError
from planet.common.params_validates import parameter_required
from planet.common.success_response import Success
from planet.config.enums import TrialCommodityStatus
from planet.models import TrialCommodity, TrialCommodityImage


class CTrialCommodity(object):

    def get_commodity_list(self):
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
        data = {"banner": banner,
                "remarks": '试用商品的一些话',
                "commodity": commodity_list
                }
        return Success(data=data)

    def get_commodity(self):
        # commodity.TCattribute = json.loads(getattr(commodity, 'TCattribute') or '[]')
        pass
