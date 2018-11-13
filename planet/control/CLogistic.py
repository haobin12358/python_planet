# -*- coding: utf-8 -*-
import json
import uuid

from flask import request

from planet.common.error_response import StatusError
from planet.common.params_validates import parameter_required
from planet.common.success_response import Success
from planet.common.token_handler import token_required
from planet.config.enums import OrderMainStatus
from planet.config.secret import kd_subscribe_api, kd_api_key, kd_api_subscribe_callbackurl
from planet.models.trade import LogisticsCompnay, OrderLogistics, OrderMain
from planet.service.STrade import STrade


class CLogistic:
    def __init__(self):
        self.strade = STrade()

    def list_company(self):
        data = parameter_required()
        kw = data.get('kw') or ''
        logistics = self.strade.get_logistics_list([
            LogisticsCompnay.LCname.contains(kw)
        ])
        return Success(data=logistics)

    @token_required
    def send(self):
        """发货"""
        data = parameter_required(('omid', 'olcompany', 'olexpressno'))
        omid = data.get('omid')
        olcompany = data.get('olcompany')
        olexpressno = data.get('olexpressno')
        with self.strade.auto_commit() as s:
            s_list = []
            order_main_instance = s.query(OrderMain).filter_by_({
                'OMid': omid,
            }).first_('订单不存在')
            if order_main_instance.OMstatus != OrderMainStatus.wait_send.value:
                raise StatusError('订单状态不正确')
            if order_main_instance.OMinRefund is True:
                raise StatusError('商品在售后状态')
            s.query(LogisticsCompnay).filter_by_({
                'LCcode': olcompany
            }).first_('快递公司不存在')
            # 添加物流记录
            order_logistics_instance = OrderLogistics.create({
                'OLid': str(uuid.uuid4()),
                'OMid': omid,
                'OLcompany': olcompany,
                'OLexpressNo': olexpressno,
            })
            s_list.append(order_logistics_instance)
            # 更改主单状态
            order_main_instance.OMstatus = OrderMainStatus.wait_recv.value
            s_list.append(order_main_instance)
            s.add_all(s_list)
            # 发送订阅信息
            # schema = 'JSON'
            # param = {
            #     'company': 'olcompany',
            #     'number': 'olexpressno',
            #     'key': kd_api_key,
            #     'parameters': {
            #         'callbackurl': kd_api_subscribe_callbackurl,
            #     }
            # }
            # data = ''
        return Success('发货成功')

    def subcribe_callback(self):
        with open('callback', 'w') as f:
            json.dump(request.detail, f)
        return 'ok'




