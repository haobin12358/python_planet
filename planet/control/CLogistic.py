# -*- coding: utf-8 -*-
import json
import uuid
from datetime import datetime

from flask import request

from planet.common.error_response import StatusError
from planet.common.logistics import Logistics
from planet.common.params_validates import parameter_required
from planet.common.request_handler import gennerc_log
from planet.common.success_response import Success
from planet.common.token_handler import token_required
from planet.config.enums import OrderMainStatus, LogisticsSignStatus
from planet.extensions.register_ext import db
from planet.models.trade import LogisticsCompnay, OrderLogistics, OrderMain
from planet.service.STrade import STrade


class CLogistic:
    def __init__(self):
        self.strade = STrade()

    def list_company(self):

        common = LogisticsCompnay.query.filter_by({
            'LCisCommon': True
        }).all()
        logistics = LogisticsCompnay.query.filter_by_().order_by(
            LogisticsCompnay.LCfirstCharater
        ).all()
        return Success(data={
            'common': common,
            'all': logistics
        })

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
        return Success('发货成功')

    def get(self):
        """获取主单物流"""
        data = parameter_required(('omid', ))
        omid = data.get('omid')
        with db.auto_commit():
            order_logistics = OrderLogistics.query.filter_by_({'OMid': omid}).first_('未获得物流信息')
            time_now = datetime.now()
            if (not order_logistics.OLdata or (time_now - order_logistics.updatetime).total_seconds() > 6 * 3600)\
                    and order_logistics.OLsignStatus != 3:  # 没有data信息或超过6小时 并且状态不是已签收
                order_logistics = self._get_logistics(order_logistics)
            logistics_company = LogisticsCompnay.query.filter_by_({'LCcode': order_logistics.OLcompany}).first()
            order_logistics.fill('OLsignStatus_en', LogisticsSignStatus(order_logistics.OLsignStatus).name)
            order_logistics.fill('logistics_company', logistics_company)
        order_logistics.OLdata = json.loads(order_logistics.OLdata)
        order_logistics.OLlastresult = json.loads(order_logistics.OLlastresult)
        return Success(data=order_logistics)

    def _get_logistics(self, order_logistics):
        # http查询
        l = Logistics()
        response = l.get_logistic(order_logistics.OLexpressNo, order_logistics.OLcompany)
        if response:
            # 插入数据库
            code = response.get('status')
            if code == '0':
                result = response.get('result')
                OrderLogisticsDict = {
                    'OLsignStatus': int(result.get('deliverystatus')),
                    'OLdata': json.dumps(result),  # 结果原字符串
                    'OLlastresult': json.dumps(result.get('list')[0])  # 最新物流
                }
                #
            else:
                OrderLogisticsDict = {
                    'OLsignStatus': -1,
                    'OLdata': json.dumps(response),  # 结果原字符串
                    'OLlastresult': '{}'
                }
            order_logistics.update(OrderLogisticsDict)
            db.session.add(order_logistics)
            # s_list.append(order_logistics)
        else:
            # 无信息 todo
            gennerc_log('物流信息出错')
        return order_logistics

    def subcribe_callback(self):
        with open('callback', 'w') as f:
            json.dump(request.detail, f)
        return 'ok'

    def _insert_to_orderlogistics(self, response, ):
        pass






