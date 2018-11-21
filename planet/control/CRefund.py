# -*- coding: utf-8 -*-
import json
import random
import time
import uuid
from datetime import datetime

from flask import request

from planet.common.error_response import ParamsError, StatusError
from planet.common.params_validates import parameter_required, validate_arg
from planet.common.success_response import Success
from planet.common.token_handler import token_required
from planet.config.enums import OrderMainStatus, ORAproductStatus, OrderRefundApplyStatus, OrderRefundORAstate, \
    DisputeTypeType, OrderRefundOrstatus
from planet.extensions.validates.trade import RefundSendForm
from planet.models.trade import OrderRefundApply, OrderMain, OrderPart, DisputeType, OrderRefund, LogisticsCompnay
from planet.service.STrade import STrade


class CRefund(object):
    def __init__(self):
        self.strade = STrade()

    @token_required
    def create(self):
        data = parameter_required(('orareason', 'oraproductstatus'))
        opid = data.get('opid')
        omid = data.get('omid')
        if opid and omid:
            raise ParamsError('omid,opid只能存在一个')
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
        """添加内置纠纷类型"""
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
        order_refund_types = DisputeType.query.filter_by_({'DItype': ditype}).order_by(DisputeType.DIsort).all()
        return Success(data=order_refund_types)

    @token_required
    def agree_apply(self):
        data = parameter_required(('oraid', 'agree'))
        oraid = data.get('oraid')
        agree = data.get('agree')
        with self.strade.auto_commit() as s:
            s_list = []
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
                    msg = '已同意, 正在退款'
                if refund_apply_instance.ORAstate == OrderRefundORAstate.goods_money.value:  # 退货退款
                    # 写入退换货表
                    orrecvname = data.get('orrecvname')
                    orrecvphone = validate_arg('^1\d{10}$', data.get('orrecvphone', ''), '输入合法的手机号码')
                    orrecvaddress = data.get('orrecvaddress')
                    try:
                        assert orrecvname and orrecvphone and orrecvaddress
                    except Exception as e:
                        raise ParamsError('请填写必要的收货信息')
                    order_refund_dict = {
                        'ORid': str(uuid.uuid4()),
                        'OMid': refund_apply_instance.OMid,
                        'OPid': refund_apply_instance.OPid,
                        'ORAid': oraid,
                        'ORrecvname': orrecvname,
                        'ORrecvphone': orrecvphone,
                        'ORrecvaddress': orrecvaddress,
                        'ORAcheckReason': request.user.id,
                    }
                    order_refund_instance = OrderRefund.create(order_refund_dict)
                    s_list.append(order_refund_instance)
                    msg = '已同意, 等待买家发货'
                refund_apply_instance.ORAstatus = OrderRefundApplyStatus.agree.value
                refund_apply_instance.ORAcheckReason = data.get('oracheckreason')
                refund_apply_instance.ORAcheckTime = datetime.now()
                s_list.append(refund_apply_instance)
            else:
                refund_apply_instance.ORAstatus = OrderRefundApplyStatus.reject.value
                refund_apply_instance.ORAcheckReason = data.get('oracheckreason')
                s_list.append(refund_apply_instance)
                msg = '拒绝成功'
            s.add_all(s_list)
        return Success(msg)

    @token_required
    def send(self):
        """买家发货"""
        form = RefundSendForm().valid_data()
        oraid = form.oraid.data
        orlogisticcompany = form.orlogisticcompany.data
        orlogisticsn = form.orlogisticsn.data
        with self.strade.auto_commit() as s:
            # 判断
            s.query(LogisticsCompnay).filter_by_({'LCcode': orlogisticcompany}).first_('物流公司不存在')
            order_refund_instance = s.query(OrderRefund).filter_by_({'ORAid': oraid}).first_('申请未同意或不存在')
            if order_refund_instance.ORstatus > OrderRefundOrstatus.wait_send.value:
                raise StatusError('重复发货')
            # 写入退货表
            order_refund_instance.update({
                'ORlogisticCompany': orlogisticcompany,
                'ORlogisticsn': orlogisticsn,
                'ORstatus': OrderRefundOrstatus.wait_recv.value,
            })
            s.add(order_refund_instance)
        return Success('发货成功')

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
            # 不改变主单的状态
            # order_main = s.query(OrderMain).filter_(
            #     OrderMain.OMid == omid,
            #     OrderMain.OMstatus.notin_([
            #         OrderMainStatus.wait_pay.value,
            #         OrderMainStatus.cancle.value,
            #         OrderMainStatus.ready.value,
            #     ]),
            #     OrderMain.USid == usid
            # ).first_('不存在的订单')
            # order_main.OMinRefund = True  # 主单状态
            # s_list.append(order_main)
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
            orastate = data.get('orastate', OrderRefundORAstate.goods_money.value)
            try:
                OrderRefundORAstate(orastate)
            except Exception as e:
                raise ParamsError('orastate参数错误')
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
                'ORAstate': orastate,
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
            # 申请参数校验
            oraproductstatus = data.get('oraproductstatus')  # 是否已经收到货
            ORAproductStatus(oraproductstatus)
            oramount = data.get('oramount')

            orastate = data.get('orastate', OrderRefundORAstate.goods_money.value)
            try:
                OrderRefundORAstate(orastate)
            except Exception as e:
                raise ParamsError('orastate参数错误')

            if not oramount or oramount > order_main.OMtrueMount:
                raise ParamsError('oramount退款金额不正确')
            # 不改变副单的状态
            # order_parts = s.query(OrderPart).filter_by_({'OMid': omid}).all()
            # for order_part in order_parts:
            #     order_part.OPisinORA = True  # 附单状态
            #     s_list.append(order_part)
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
                'ORAstate': orastate,
            }
            order_refund_apply_instance = OrderRefundApply.create(order_refund_apply_dict)
            s_list.append(order_refund_apply_instance)
            s.add_all(s_list)
