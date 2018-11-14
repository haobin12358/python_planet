# -*- coding: utf-8 -*-
from planet.common.base_resource import Resource
from planet.control.CCoupon import CCoupon


class ACoupon(Resource):
    def __init__(self):
        self.ccoupon = CCoupon()

    def get(self, coupon):
        apis = {
            'list_user_coupon': self.ccoupon.list_user_coupon,
        }
        return apis

    def post(self, coupon):
        apis = {
            'post': self.ccoupon.create,
            'update': self.ccoupon.update,
        }
        return apis
