# -*- coding: utf-8 -*-
from planet.common.base_resource import Resource
from planet.control.COrder import COrder


class AOrder(Resource):
    def __init__(self):
        self.corder = COrder()

    def post(self, order):
        apis = {
            'create': self.corder.create,
            'pay': self.corder.pay,
            'alipay_notify': self.corder.alipay_notify,
            'wechat_notify': self.corder.wechat_notify,
            'create_evaluation': self.corder.create_order_evaluation,
            'del_evaluation': self.corder.del_evaluation,
            'cancle': self.corder.cancle,
            'delete': self.corder.delete,
            'order_coupons': self.corder.get_can_use_coupon,  # 创建订单时可以使用的优惠券
            'order_feight': self.corder.get_order_feight,
            'confirm': self.corder.confirm,
            'update_price': self.corder.update_price,
            'autoevaluation': self.corder.set_autoevaluation_time,
            'test_to_pay': self.corder.test_to_pay,   # 测试接口 注意删除
            'test_to_send': self.corder.test_to_send,   # 测试接口 注意删除
            'get_preview_commision': self.corder.get_preview_commision,
        }
        return apis

    def get(self, order):
        apis = {
            'list': self.corder.list,
            'get': self.corder.get,
            'count': self.corder.get_order_count,
            'evaluation': self.corder.get_evaluation,
            'history_detail': self.corder.history_detail,
            'autoevaluation': self.corder.get_autoevaluation_time,
            'export_xls': self.corder.export_xls,
        }
        return apis

