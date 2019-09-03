import uuid

from flask import request

from planet.common.error_response import ParamsError, StatusError
from planet.common.params_validates import parameter_required
from planet.config.enums import ApplyStatus
from planet.control.CRefund import CRefund
from planet.models import OrderArbtrationApply, OrderMain, OrderRefundApply, OrderPart


class CArbtratin(CRefund):
    def create(self):
        data = parameter_required(('oaareason', 'oaaproductstatus'))
        omid = data.get('omid')
        opid = data.get('opid')
        if omid and opid:
            raise ParamsError('主单和副单只能选择一个发起仲裁')
        self.check_qualification(opid, omid)
        oaaaddtionvoucher = data.get('oaaaddtionvoucher')
        oaa_instance = OrderArbtrationApply.create({
            'OAAid': str(uuid.uuid1()),
            'OAAsn': self._generic_no(),
            'OMid': omid,
            'OPid': opid,
            'USid': request.user.id,
            'OAAreason': data.get('oaareason'),
            'OAAaddtion': data.get('oaaaddtion'),

        })

    def check_qualification(self, opid=None, omid=None):
        if omid:
            om = OrderMain.query.filter(OrderMain.OMid == omid, OrderMain.isdelete == False).first()
            if not om:
                raise ParamsError('订单已删除')

            if om.OMinRefund == False:
                raise ParamsError('请对已发起售后的商品订单发起仲裁')

            ora = OrderRefundApply.query.filter(
                OrderRefundApply.isdelete == False,
                OrderRefundApply.OMid == omid,
                OrderRefundApply.ORAstatus == ApplyStatus.reject.value).first()

            if not ora:
                raise StatusError('该售后处理中，请等待处理结果')

        if opid:
            op = OrderPart.query.filter(
                OrderPart.OPid == opid,
                OrderPart.isdelete == False
            ).first()

            if not op:
                raise ParamsError('副单已删除')
            if op.OPisinORA == False:
                raise StatusError('请对已发起售后的订单发起仲裁')

            ora = OrderRefundApply.query.filter(
                OrderRefundApply.OPid == opid,
                OrderRefundApply.isdelete == False,
                OrderRefundApply.ORAstatus == ApplyStatus.reject.value).first()

            if not ora:
                raise StatusError('该订单售后处理中，请等待处理结果')

