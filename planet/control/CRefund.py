# -*- coding: utf-8 -*-
import json
import random
import time
import uuid

from flask import request

from planet.common.error_response import ParamsError
from planet.common.params_validates import parameter_required
from planet.common.success_response import Success
from planet.common.token_handler import token_required
from planet.config.enums import OrderMainStatus, ORAproductStatus
from planet.models.trade import OrderRefundApply, OrderMain, OrderPart
from planet.service.STrade import STrade


class CRefund(object):
    def __init__(self):
        self.strade = STrade()

    @token_required
    def create(self):
        data = parameter_required(('opid', 'orareason', 'oraproductstatus'))
        opid = data.get('opid')
        usid = request.user.id
        with self.strade.auto_commit() as s:
            s_list = []
            # 副单进入售后状态
            order_part = s.query(OrderPart).filter_by_({
                'OPid': opid,
                'OPisinORA': False
            }).first_('不存在的订单详情')
            order_part.OPisinORA = True  # 改为售后状态
            s_list.append(order_part)
            # 主单售后状态
            omid = order_part.OMid
            order_main = s.query(OrderMain).filter_(
                OrderMain.OMid == omid,
                OrderMain.OMstatus.notin_([
                    OrderMainStatus.wait_pay.value,
                    OrderMainStatus.cancle.value,
                    OrderMainStatus.ready.value,
                ]),
                OrderMain.USid == usid
            ).first_('不存在的订单')
            order_main.OMinRefund = True  # 存在售后商品
            s_list.append(order_main)
            # 售后申请表
            # 参数
            oraproductstatus = data.get('oraproductstatus')
            ORAproductStatus(oraproductstatus)
            oramount = data.get('oramount')
            if not oramount or oramount > order_part.OPsubTotal:
                raise ParamsError('oramount退款金额不正确')
            oraddtionvoucher = data.get('oraddtionvoucher')
            if oraddtionvoucher and isinstance(oraddtionvoucher, list):
                oraddtionvoucher = json.dumps(oraddtionvoucher)
            else:
                oraddtionvoucher = None
            oraaddtion = data.get('oraaddtion')
            # 添加
            order_refund_apply_dict = {
                'ORAid': str(uuid.uuid4()),
                'OMid': omid,
                'ORAsn': self._generic_no(),
                'OPid': opid,
                'USid': usid,
                'ORAmount': oramount,
                'ORaddtionVoucher': oraddtionvoucher,
                'ORAaddtion': oraaddtion,
                'ORAreason': data.get('orareason'),
                'ORAproductStatus': oraproductstatus,
            }
            order_refund_apply_instance = OrderRefundApply.create(order_refund_apply_dict)
            s_list.append(order_refund_apply_instance)
            s.add_all(s_list)
        return Success('申请成功, 等待答复')

    @staticmethod
    def _generic_no():
        """生成退款号"""
        return str(time.strftime('%Y%m%d%H%M%S', time.localtime(time.time()))) + \
               str(time.time()).replace('.', '')[-7:] + str(random.randint(1000, 9999))

