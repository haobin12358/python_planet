# -*- coding: utf-8 -*-
import json
import random
import time
import uuid
from datetime import datetime
from decimal import Decimal

from flask import request, current_app
from sqlalchemy import or_

from planet.common.error_response import ParamsError, StatusError, ApiError, DumpliError
from planet.common.params_validates import parameter_required, validate_arg
from planet.common.success_response import Success
from planet.common.token_handler import token_required
from planet.config.enums import OrderMainStatus, ORAproductStatus, ApplyStatus, OrderRefundORAstate, \
    DisputeTypeType, OrderRefundOrstatus, PayType, UserCommissionStatus
from planet.extensions.register_ext import wx_pay, alipay, db
from planet.extensions.validates.trade import RefundSendForm, RefundConfirmForm, RefundConfirmRecvForm
from planet.models import UserCommission
from planet.models.trade import OrderRefundApply, OrderMain, OrderPart, DisputeType, OrderRefund, LogisticsCompnay, \
    OrderRefundFlow, OrderPay, OrderRefundNotes
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
    def cancle(self):
        """撤销"""
        data = parameter_required(('oraid', ))
        oraid = data.get('oraid')
        with db.auto_commit():
            order_refund_apply = OrderRefundApply.query.filter_by({
                'isdelete': False,
                'ORAid': oraid,
                "USid": request.user.id,
                'ORAstatus': ApplyStatus.wait_check.value
            }).first_('售后已处理')

            order_refund_apply.update({
                'ORAstatus': ApplyStatus.cancle.value
            })
            db.session.add(order_refund_apply)
            # 修改主单或副单售后状态
            if order_refund_apply.OPid:
                OrderPart.query.filter_by({
                    'OPid': order_refund_apply.OPid
                }).update({
                    'OPisinORA': False
                })
            if order_refund_apply.OMid:
                OrderMain.query.filter_by({
                    'OMid': order_refund_apply.OMid
                }).update({
                    "OMinRefund": False
                })
            # 对应退货流水表改为已取消
            OrderRefund.query.filter(
                OrderRefund.ORAid == oraid,
                OrderRefund.isdelete == False
            ).update({
                'ORstatus': OrderRefundOrstatus.cancle.value
            })
        return Success('撤销成功')

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
            diid = str(uuid.uuid1())
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
        """同意退款"""
        data = parameter_required(('oraid', 'agree'))
        oraid = data.get('oraid')
        agree = data.get('agree')
        with self.strade.auto_commit() as s:
            s_list = []
            refund_apply_instance = s.query(OrderRefundApply).filter_by_({'ORAid': oraid, 'ORAstatus': ApplyStatus.wait_check.value }).first_('申请已处理或不存在')
            refund_apply_instance.ORAcheckTime = datetime.now()
            # 获取订单
            if refund_apply_instance.OMid:
                order_main_instance = s.query(OrderMain).filter_by({'OMid': refund_apply_instance.OMid}).first()
            else:
                order_part_instance = s.query(OrderPart).filter(OrderPart.OPid == refund_apply_instance.OPid).first()
                order_main_instance = s.query(OrderMain).filter_by({'OMid': order_part_instance.OMid}).first()
            if agree is True:
                refund_apply_instance.ORAstatus = ApplyStatus.agree.value
                if refund_apply_instance.ORAstate == OrderRefundORAstate.only_money.value:  # 仅退款
                    # 退款流水表
                    order_pay_instance = s.query(OrderPay).filter(
                        OrderPay.isdelete == False,
                        OrderPay.OPayno == order_main_instance.OPayno
                    ).first()
                    refund_flow_instance = OrderRefundFlow.create({
                        'ORFid': str(uuid.uuid1()),
                        'ORAid': oraid,
                        'ORAmount': refund_apply_instance.ORAmount,
                        'OPayno': order_main_instance.OPayno,
                        'OPayType': order_pay_instance.OPayType,
                    })
                    s_list.append(refund_flow_instance)
                    # mount = refund_apply_instance.ORAmount # todo 退款金额需要改正
                    # old_total_fee = order_pay_instance.OPayMount
                    mount = 0.01
                    old_total_fee = 0.01
                    current_app.logger.info('正在退款中 {} '.format(refund_apply_instance.ORAmount))

                    self._refund_to_user(  # 执行退款, 待测试
                        out_trade_no=order_main_instance.OPayno,
                        out_request_no=oraid,
                        mount=mount,
                        opaytype=order_pay_instance.OPayType,
                        old_total_fee=old_total_fee
                    )
                    msg = '已同意, 正在退款'
                    # 佣金退
                    if refund_apply_instance.OPid:
                        self._cancle_commision(order_part=order_part_instance)
                    if refund_apply_instance.OMid:
                        self._cancle_commision(order_main=order_main_instance)

                if refund_apply_instance.ORAstate == OrderRefundORAstate.goods_money.value:  # 退货退款
                    # 取消原来的退货表, (主要是因为因为可能因撤销为未完全删除)
                    old_order_refund = OrderRefund.query.filter(OrderRefund.isdelete == False,
                                                                OrderRefund.ORAid == oraid).update({
                        'ORstatus': OrderRefundOrstatus.cancle.value
                    })
                    # 写入退换货表
                    orrecvname = data.get('orrecvname')
                    orrecvphone = validate_arg('^1\d{10}$', data.get('orrecvphone', ''), '输入合法的手机号码')
                    orrecvaddress = data.get('orrecvaddress')
                    try:
                        assert orrecvname and orrecvphone and orrecvaddress
                    except Exception as e:
                        raise ParamsError('请填写必要的收货信息')

                    order_refund_dict = {
                        'ORid': str(uuid.uuid1()),
                        'OMid': refund_apply_instance.OMid,
                        'OPid': refund_apply_instance.OPid,
                        'ORAid': oraid,
                        'ORrecvname': orrecvname,
                        'ORrecvphone': orrecvphone,
                        'ORrecvaddress': orrecvaddress,
                    }
                    order_refund_instance = OrderRefund.create(order_refund_dict)
                    s_list.append(order_refund_instance)
                    msg = '已同意, 等待买家发货'
                refund_apply_instance.ORAstatus = ApplyStatus.agree.value
            else:
                refund_apply_instance.ORAstatus = ApplyStatus.reject.value
                if refund_apply_instance.OMid:
                    order_main_instance.OMinRefund = False
                    db.session.add(order_main_instance)
                    db.session.add(OrderRefundNotes.create({
                        'ORNid': str(uuid.uuid1()),
                        'OMid': refund_apply_instance.OMid,
                        'UserName': request.user.username,
                        'USid': request.user.id,
                        'ORNaction': -1,  # 拒绝
                        'ORNabo': data.get('oracheckreason')
                    }))
                else:
                    order_part_instance.OPisinORA = False
                    db.session.add(order_part_instance)
                    db.session.add(OrderRefundNotes.create({
                        'ORNid': str(uuid.uuid1()),
                        'OPid': order_part_instance.OPid,
                        'UserName': request.user.username,
                        'USid': request.user.id,
                        'ORNaction': -1,  # 拒绝
                        'ORNabo': data.get('oracheckreason')
                    }))
                msg = '拒绝成功'
            refund_apply_instance.ORAcheckReason = data.get('oracheckreason')
            refund_apply_instance.ORAcheckTime = datetime.now()
            refund_apply_instance.ORAcheckUser = request.user.id
            s_list.append(refund_apply_instance)
            s.add_all(s_list)
        return Success(msg)

    @token_required
    def back_confirm_refund(self):
        """执行退款退款中的最后一步, 退款"""
        form = RefundConfirmForm().valid_data()
        oraid = form.oraid.data
        agree = form.agree.data
        with db.auto_commit():
            refund_apply_instance = OrderRefundApply.query.filter(
                OrderRefundApply.isdelete == False,
                OrderRefundApply.ORAid == oraid,
                OrderRefundApply.ORAstatus == ApplyStatus.agree.value,
                OrderRefundApply.ORAstate == OrderRefundORAstate.goods_money.value
            ).first_('对应的退货申请不存在或未同意')

            if refund_apply_instance.OMid:
                order_main_instance = OrderMain.query.filter_by({'OMid': refund_apply_instance.OMid}).first()
            else:
                order_part_instance = OrderPart.query.filter(OrderPart.OPid == refund_apply_instance.OPid).first()
                order_main_instance = OrderMain.query.filter_by({'OMid': order_part_instance.OMid}).first()
            order_refund = OrderRefund.query.filter(
                OrderRefund.isdelete == False,
                OrderRefund.ORstatus == OrderRefundOrstatus.ready_recv.value,  # 确认收货后执行退款
                OrderRefund.ORAid == oraid
            ).first_('请确认收货后退款')
            if agree is True:
                order_pay_instance = OrderPay.query.filter(
                    OrderPay.isdelete == False,
                    OrderPay.OPayno == order_main_instance.OPayno
                ).first()
                order_refund.ORstatus = OrderRefundOrstatus.ready_refund.value
                db.session.add(order_refund)
                # TODO 执行退款
                # mount = refund_apply_instance.ORAmount # todo 退款金额需要改正
                # old_total_fee = order_pay_instance.OPayMount
                refund_flow_instance = OrderRefundFlow.create({
                    'ORFid': str(uuid.uuid1()),
                    'ORAid': oraid,
                    'ORAmount': refund_apply_instance.ORAmount,
                    'OPayno': order_main_instance.OPayno,
                    'OPayType': order_pay_instance.OPayType,
                })
                db.session.add(refund_flow_instance)
                mount = 0.01
                old_total_fee = 0.01
                self._refund_to_user(  # 执行退款, 待测试
                    out_trade_no=order_main_instance.OPayno,
                    out_request_no=oraid,
                    mount=mount,
                    opaytype=order_pay_instance.OPayType,
                    old_total_fee=old_total_fee
                )
                msg = '已同意, 正在退款'
            elif agree is False:
                order_refund.ORstatus = OrderRefundOrstatus.reject.value
                db.session.add(order_refund)
                msg = '已拒绝'
            else:
                raise ParamsError('agree 参数错误')
        return Success(msg)

    @token_required
    def back_confirm_recv(self):
        """后台确认收货"""
        form = RefundConfirmRecvForm().valid_data()
        oraid = form.oraid.data
        with db.auto_commit():
            OrderRefundApply.query.filter(
                OrderRefundApply.isdelete == False,
                OrderRefundApply.ORAid == oraid,
                OrderRefundApply.ORAstatus == ApplyStatus.agree.value,
                OrderRefundApply.ORAstate == OrderRefundORAstate.goods_money.value
            ).first_('对应的退货申请不存在或未同意')
            order_refund = OrderRefund.query.filter(
                OrderRefund.isdelete == False,
                OrderRefund.ORstatus >= OrderRefundOrstatus.wait_recv.value,  # 确认收货后执行退款
                OrderRefund.ORAid == oraid
            ).first_('未发货')
            order_refund.ORstatus = OrderRefundOrstatus.ready_recv.value
            db.session.add(order_refund)
            msg = '已收货'
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

    @token_required
    def refund_query(self):
        """查询退款结果"""
        # todo 查询退款结果

    @staticmethod
    def _generic_no():
        """生成退款号"""
        return str(time.strftime('%Y%m%d%H%M%S', time.localtime(time.time()))) + \
               str(time.time()).replace('.', '')[-7:] + str(random.randint(1000, 9999))

    def _order_part_refund(self, opid, usid, data):
        with self.strade.auto_commit() as s:
            s_list = []
            # 副单
            order_part = s.query(OrderPart).filter(
                OrderPart.OPid == opid,
                OrderPart.isdelete == False
            ).first_('不存在的订单详情')
            # 删除原来的
            OrderRefundNotes.query.filter(
                OrderRefundNotes.isdelete == False,
                OrderRefundNotes.OPid == order_part.OPid
            ).delete_()
            # 所在主单的副单个数
            order_part_count = OrderPart.query.filter_by_({
                'OMid': order_part.OMid
            }).count()
            current_app.logger.info('当前副单所在主单有 {} 个商品'.format(order_part_count))
            if order_part_count == 1:
                # 如果只有一个副单, 则改为申请主单售后
                current_app.logger.info('改为主单售后')
                return self._order_main_refund(order_part.OMid, usid, data)

            # 副单售后
            if order_part.OPisinORA is True:
                cancled_apply = OrderRefundApply.query.filter_by_({
                    'ORAstatus': ApplyStatus.cancle.value,
                    'OPid': opid
                }).first()
                if not cancled_apply:
                    raise DumpliError('重复申请')
                # 删除之前已经撤销的售后
                cancled_apply.isdelete = True
                s_list.append(cancled_apply)
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
            if order_main.OMinRefund == True:
                raise DumpliError('主订单已在售后中, 请勿重复申请')
            apply = OrderRefundApply.query.filter(
                OrderRefundApply.OPid == opid,
                OrderRefundApply.isdelete == False,
                OrderRefundApply.ORAstatus != ApplyStatus.reject.value).first()
            if apply and apply.ORAstatus != ApplyStatus.cancle.value:
                raise DumpliError('订单已在售后中, 请勿重复申请')
            elif apply:
                current_app.logger.info('删除原来副单售后申请')
                apply.isdelete = True
                s_list.append(apply)
            # 不改变主单的状态
            # order_main.OMinRefund = True  # 主单状态
            # s_list.append(order_main)

            order_part.OPisinORA = True  # 附单状态
            s_list.append(order_part)
            # 申请参数校验
            oraproductstatus = data.get('oraproductstatus')
            ORAproductStatus(oraproductstatus)
            oramount = data.get('oramount')
            if oramount:
                oramount = Decimal(str((oramount)))
            if not oramount or oramount > order_part.OPsubTrueTotal:
                raise ParamsError('退款金额不正确')
            oraddtionvoucher = data.get('oraddtionvoucher')
            if oraddtionvoucher and isinstance(oraddtionvoucher, list):
                oraddtionvoucher = oraddtionvoucher
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
                'ORAid': str(uuid.uuid1()),
                # 'OMid': omid,
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
            current_app.logger.info('the order_part refund apply id(oraid) is {}'.format(order_refund_apply_dict['ORAid']))

    def _order_main_refund(self, omid, usid, data):
        with self.strade.auto_commit() as s:
            s_list = []
            OrderRefundNotes.query.filter(
                OrderRefundNotes.isdelete == False,
                OrderRefundNotes.OMid == omid
            ).delete_()
            order_main = s.query(OrderMain).filter_(
                OrderMain.OMid == omid,
                OrderMain.OMstatus.notin_([
                    OrderMainStatus.wait_pay.value,
                    OrderMainStatus.cancle.value,
                    OrderMainStatus.ready.value,
                ]),
                OrderMain.USid == usid
            ).first_('不存在的订单')
            if order_main.OMinRefund is True:
                raise DumpliError('已经在售后中')
            # 之前的申请
            apply = OrderRefundApply.query.filter(
                OrderRefundApply.isdelete == False,
                OrderRefundApply.OMid == order_main.OMid,
                OrderRefundApply.ORAstatus.notin_([
                    ApplyStatus.reject.value,
                    ApplyStatus.cancle.value,
                ]),
            ).first()
            if apply:
                raise DumpliError('订单已在售后中, 请勿重复申请')
            if apply:
                apply.isdelete = True
                s_list.append(apply)
            # 申请主单售后, 所有的副单不可以有在未撤销的售后状态或未被拒绝
            order_parts_in_refund = OrderPart.query.filter_by_({
                'OMid': omid,
                'OPisinORA': True
            }).all()
            for order_part in order_parts_in_refund:
                part_apply = OrderRefundApply.query.filter_by_({
                    'OPid': order_part.OPid
                }).first()
                # if not cancled_apply:
                #     raise DumpliError('订单中有商品已在售后中, 请勿重复申请')
                if part_apply and part_apply.ORAstatus != ApplyStatus.cancle.value:
                    raise DumpliError('订单中有商品已在售后中, 请勿重复申请')
                elif part_apply:
                    part_apply.isdelete = True
                    s_list.append(part_apply)
            order_main.OMinRefund = True  # 主单状态
            s_list.append(order_main)
            # 申请参数校验
            oraproductstatus = int(data.get('oraproductstatus'))  # 是否已经收到货
            ORAproductStatus(oraproductstatus)

            orastate = int(data.get('orastate', OrderRefundORAstate.goods_money.value))
            try:
                OrderRefundORAstate(orastate)
            except Exception as e:
                raise ParamsError('orastate参数错误')
            oramount = data.get('oramount')
            if oramount:
                oramount = Decimal(str(oramount))
            if not oramount or oramount > order_main.OMtrueMount:
                raise ParamsError('oramount退款金额不正确')
            # 不改变副单的状态
            # order_parts = s.query(OrderPart).filter_by_({'OMid': omid}).all()
            # for order_part in order_parts:
            #     order_part.OPisinORA = True  # 附单状态
            #     s_list.append(order_part)
            # 添加申请表
            oraddtionvoucher = data.get('oraddtionvoucher')
            oraaddtion = data.get('oraaddtion')
            order_refund_apply_dict = {
                'ORAid': str(uuid.uuid1()),
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
            current_app.logger.info('the order_main refund apply id(oraid) is {}'.format(order_refund_apply_dict['ORAid']))

    def _refund_to_user(self, out_trade_no, out_request_no, mount, opaytype, old_total_fee=None):
        """
        执行退款
        mount 单位元
        old_total_fee 单位元
        out_request_no
        :return:
        """
        if opaytype == PayType.wechat_pay.value:  # 微信
            mount = int(mount * 100)
            old_total_fee = int(Decimal(str(old_total_fee) ) * 100)
            current_app.logger.info('the total fee to refund cent is {}'.format(mount))
            result = wx_pay.refund(
                out_trade_no=out_trade_no,
                out_refund_no=out_request_no,
                total_fee=old_total_fee,  # 原支付的金额
                refund_fee=mount  # 退款的金额
            )

        else:  # 支付宝
            result = alipay.api_alipay_trade_refund(
                out_trade_no=out_trade_no,
                out_request_no=out_request_no,
                refund_amount=mount
            )
            if result["code"] != "10000":
                raise ApiError('退款错误')
        return result

    def _cancle_commision(self, *args, **kwargs):
        order_main = kwargs.get('order_main')
        order_part = kwargs.get('order_part')
        if order_main:
            order_parts = OrderPart.query.filter(
                OrderPart.isdelete == False,
                OrderPart.OMid == order_main.OMid
            ).all()
            for order_part in order_parts:
                self._cancle_commision(order_part=order_part)
        elif order_part:
            user_commision = UserCommission.query.filter(
                UserCommission.isdelete == False,
                UserCommission.OPid == order_part.OPid,
                UserCommission.UCstatus == UserCommissionStatus.preview.value
            ).update({
                'UCstatus': UserCommissionStatus.error.value
            })
            current_app.logger.info('失效了{}个佣金到账(包括供应商到账, 平台到账)'.format(user_commision))

# todo 售后物流