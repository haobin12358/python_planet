# -*- coding: utf-8 -*-
import json
import random
import time
import uuid
from datetime import datetime

from flask import request

from planet.common.error_response import ParamsError
from planet.common.params_validates import parameter_required
from planet.common.success_response import Success
from planet.common.token_handler import token_required
from planet.config.enums import OrderMainStatus, ORAproductStatus, OrderRefundApplyStatus, OrderRefundORAstate, DisputeTypeType
from planet.models.trade import OrderRefundApply, OrderMain, OrderPart, DisputeType
from planet.service.STrade import STrade


class CRefund(object):
    def __init__(self):
        self.strade = STrade()

    @token_required
    def create(self):
        data = parameter_required(('orareason', 'oraproductstatus'))
        opid = data.get('opid')
        omid = data.get('omid')
        usid = request.user.id
        if opid:
            # 单个商品售后
            self._order_part_refund(opid, usid, data)
        elif omid:
            # 主单售后
            self._order_main_refund(omid, usid, data)
        else:
            raise ParamsError('须指定主单或副单')
        return Success('申请成功, 等待答复')

    @token_required
    def create_dispute_type(self):
        """添加申请理由表"""
        data = parameter_required(('diname', 'ditype', 'disort'))
        diname = data.get('diname')
        ditype = data.get('ditype')
        try:
            DisputeTypeType(ditype)
            disort = int(data.get('disort'))
        except Exception as e:
            raise ParamsError('ditype错误')
        with self.strade.auto_commit() as s:
            diid = str(uuid.uuid4())
            dispute_type_dict = {
                'DIid': diid,
                'DIname': diname,
                'DItype': ditype,
                'DIsort': disort
            }
            dispute_type_instance = DisputeType.create(dispute_type_dict)
            s.add(dispute_type_instance)
        return Success('创建成功', data={'diid': diid})

    def list_dispute_type(self):
        """获取纠纷类型"""
        data = parameter_required()
        ditype = data.get('type') or None
        order_refund_types = DisputeType.query.filter_by_({'DItype': ditype}).all()
        return Success(data=order_refund_types)


    @token_required
    def agree_apply(self):
        data = parameter_required(('oraid', 'agree'))
        oraid = data.get('oraid')
        agree = data.get('agree')
        with self.strade.auto_commit() as s:
            refund_apply_instance = s.query(OrderRefundApply).filter_by_({
                'ORAid': oraid,
                'ORAstatus': OrderRefundApplyStatus.wait_check.value
            }).first_('申请已处理或不存在')
            refund_apply_instance.ORAcheckTime = datetime.now()
            if agree is True:
                refund_apply_instance.ORAstatus = OrderRefundApplyStatus.agree.value
                if refund_apply_instance.ORAstate == OrderRefundORAstate.only_money.value:  # 仅退款
                    # todo 退款
                    pass
                if refund_apply_instance.ORAstate == OrderRefundORAstate.goods_money.value:  # 退货退款
                    # 写入退换货表
                    pass
            else:
                refund_apply_instance.ORAstatus = OrderRefundApplyStatus.reject.value
                refund_apply_instance.ORAcheckReason = data.get('oracheckreason')

    def send(self):
        """买家发货"""
        pass

    @staticmethod
    def _generic_no():
        """生成退款号"""
        return str(time.strftime('%Y%m%d%H%M%S', time.localtime(time.time()))) + \
               str(time.time()).replace('.', '')[-7:] + str(random.randint(1000, 9999))

    def _order_part_refund(self, opid, usid, data):
        with self.strade.auto_commit() as s:
            s_list = []
            # 副单进入售后状态
            order_part = s.query(OrderPart).filter_by_({
                'OPid': opid,
                'OPisinORA': False
            }).first_('不存在的订单详情')
            order_part.OPisinORA = True  # 附单状态
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
            order_main.OMinRefund = True  # 主单状态
            s_list.append(order_main)
            # 申请参数校验
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
            # 添加申请表
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

    def _order_main_refund(self, omid, usid, data):
        with self.strade.auto_commit() as s:
            s_list = []
            order_main = s.query(OrderMain).filter_(
                OrderMain.OMid == omid,
                OrderMain.OMstatus.notin_([
                    OrderMainStatus.wait_pay.value,
                    OrderMainStatus.cancle.value,
                    OrderMainStatus.ready.value,
                ]),
                OrderMain.USid == usid
            ).first_('不存在的订单')
            order_main.OMinRefund = True  # 主单状态
            s_list.append(order_main)
            # 副单状态
            # 申请参数校验
            oraproductstatus = data.get('oraproductstatus')
            ORAproductStatus(oraproductstatus)
            oramount = data.get('oramount')
            if not oramount or oramount > order_main.OMtrueMount:
                raise ParamsError('oramount退款金额不正确')
            order_parts = s.query(OrderPart).filter_by_({'OMid': omid}).all()
            for order_part in order_parts:
                order_part.OPisinORA = True  # 附单状态
                s_list.append(order_part)
            # 添加申请表
            oraddtionvoucher = data.get('oraddtionvoucher')
            if oraddtionvoucher and isinstance(oraddtionvoucher, list):
                oraddtionvoucher = json.dumps(oraddtionvoucher)
            oraaddtion = data.get('oraaddtion')
            order_refund_apply_dict = {
                'ORAid': str(uuid.uuid4()),
                'OMid': omid,
                'ORAsn': self._generic_no(),
                'USid': usid,
                'ORAmount': oramount,
                'ORaddtionVoucher': oraddtionvoucher,
                'ORAaddtion': oraaddtion,
                'ORAreason': data.get('orareason'),
                'ORAproductStatus': oraproductstatus,
            }
            order_refund_apply_instance = OrderRefundApply.create(order_refund_apply_dict)
            s_list.append(order_refund_apply_instance)
