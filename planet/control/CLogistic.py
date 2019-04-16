# -*- coding: utf-8 -*-
import json
import uuid
from datetime import datetime

from flask import request, current_app

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
            # if order_main_instance.OMstatus != OrderMainStatus.wait_send.value:
            #     raise StatusError('订单状态不正确')
            if order_main_instance.OMinRefund is True:
                raise StatusError('商品在售后状态')
            s.query(LogisticsCompnay).filter_by_({
                'LCcode': olcompany
            }).first_('快递公司不存在')
            # 之前物流记录判断
            order_logistics_instance_old = OrderLogistics.query.filter(
                OrderLogistics.OMid == omid,
                OrderLogistics.isdelete == False,
            ).first()
            if order_logistics_instance_old:
                order_logistics_instance_old.isdelete = True

            # 添加物流记录
            order_logistics_instance = OrderLogistics.create({
                'OLid': str(uuid.uuid1()),
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
    #
    # def update(self):
    #     data = parameter_required(('omid', 'olcompany', 'olexpressno'))
    #     omid = data.get('omid')
    #     olcompany = data.get('olcompany')
    #     olexpressno = data.get('olexpressno')
    #     with self.strade.auto_commit() as s:
    #         s_list = []
    #         order_main_instance = s.query(OrderMain).filter_by_({
    #             'OMid': omid,
    #         }).first_('订单不存在')
    #         if order_main_instance.OMstatus != OrderMainStatus.wait_recv.value:
    #             raise StatusError('订单状态不正确')
    #         if order_main_instance.OMinRefund is True:
    #             raise StatusError('商品在售后状态')
    #         s.query(LogisticsCompnay).filter_by_({
    #             'LCcode': olcompany
    #         }).first_('快递公司不存在')
    #         # 之前物流记录判断
    #         order_logistics_instance_old = OrderLogistics.query.filter(
    #             OrderLogistics.OMid == omid,
    #             OrderLogistics.isdelete == False,
    #         ).first()
    #         if order_logistics_instance_old:
    #             order_logistics_instance_old.isdelete = True
    #
    #         # 添加物流记录
    #         order_logistics_instance = OrderLogistics.create({
    #             'OLid': str(uuid.uuid4()),
    #             'OMid': omid,
    #             'OLcompany': olcompany,
    #             'OLexpressNo': olexpressno,
    #         })
    #         s_list.append(order_logistics_instance)
    #         # 更改主单状态
    #         order_main_instance.OMstatus = OrderMainStatus.wait_recv.value
    #         s_list.append(order_main_instance)
    #         s.add_all(s_list)
    #     return Success('发货成功')

    def get(self):
        """获取主单物流"""
        data = parameter_required(('omid', ))
        omid = data.get('omid')
        with db.auto_commit():
            order_logistics = OrderLogistics.query.filter_by_({'OMid': omid}).first_('未获得物流信息')
            time_now = datetime.now()
            if order_logistics.OLdata:
                oldata = json.loads(order_logistics.OLdata)
                if not oldata:
                    oldata_status = False
                else:
                    oldata_status = oldata.get('status')
                    if str(oldata_status) == "205":
                        oldata_status = False
                    else:
                        oldata_status = True
            else:
                oldata_status = False

            # 没有data信息或超过6小时 并且状态不是已签收
            if ((not oldata_status or (time_now - order_logistics.updatetime).total_seconds() > 6 * 3600)
                    and order_logistics.OLsignStatus != LogisticsSignStatus.already_signed.value):
                order_logistics = self._get_logistics(order_logistics)
            logistics_company = LogisticsCompnay.query.filter_by_({'LCcode': order_logistics.OLcompany}).first()
            order_logistics.fill('OLsignStatus_en', LogisticsSignStatus(order_logistics.OLsignStatus).name)
            order_logistics.fill('OLsignStatus_zh', LogisticsSignStatus(order_logistics.OLsignStatus).zh_value)
            order_logistics.fill('logistics_company', logistics_company)
        order_logistics.OLdata = json.loads(order_logistics.OLdata)
        order_logistics.OLlastresult = json.loads(order_logistics.OLlastresult)
        return Success(data=order_logistics)

    def _get_logistics(self, order_logistics):
        # http查询
        l = Logistics()
        response = l.get_logistic(order_logistics.OLexpressNo, order_logistics.OLcompany)
        current_app.logger.info("物流记录OLid--> {} ；".format(order_logistics.OLid))
        if response:
            # 插入数据库
            code = response.get('status')
            if code == '0':
                result = response.get('result')
                OrderLogisticsDict = {
                    'OLsignStatus': int(result.get('deliverystatus')),
                    'OLdata': json.dumps(result),  # 快递结果原字符串
                    'OLlastresult': json.dumps(result.get('list')[0])  # 最新物流
                }
                #
            elif code == '205':  # 205 暂时没有信息，可能在揽件过程中
                OrderLogisticsDict = {
                    'OLsignStatus': 0,  # 签收状态 0：快递收件(揽件) 1.在途中 2.正在派件 3.已签收 4.派送失败 -1 异常数据'
                    'OLdata': json.dumps(response),  # 整体结果原字符串
                    'OLlastresult': '{}'
                }
            else:
                OrderLogisticsDict = {
                    'OLsignStatus': -1,
                    'OLdata': json.dumps(response),  # 结果原字符串
                    'OLlastresult': '{}'
                }
                order_main = OrderMain.query.filter(
                    OrderMain.OMid == order_logistics.OMid,
                    OrderMain.isdelete == False
                ).first()
                order_main.update({'OMstatus': OrderMainStatus.wait_send.value})
                db.session.add(order_main)

            # s_list.append(order_logistics)
        else:
            # 无信息 todo
            OrderLogisticsDict = {
                'OLsignStatus': -1,
                'OLdata': "[]",  # 结果原字符串
                'OLlastresult': '{}'
            }
            order_main = OrderMain.query.filter(
                OrderMain.OMid == order_logistics.OMid,
                OrderMain.isdelete == False
            ).first()
            order_main.update({'OMstatus': OrderMainStatus.wait_send.value})
            db.session.add(order_main)
            gennerc_log('物流信息出错')
        order_logistics.update(OrderLogisticsDict)
        db.session.add(order_logistics)
        return order_logistics

    def subcribe_callback(self):
        with open('callback', 'w') as f:
            json.dump(request.detail, f)
        return 'ok'

    def _insert_to_orderlogistics(self, response, ):
        pass






