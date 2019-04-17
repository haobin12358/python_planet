# -*- coding: utf-8 -*-
from planet.common.base_resource import Resource
from planet.control.CCoupon import CCoupon


class ACoupon(Resource):
    def __init__(self):
        self.ccoupon = CCoupon()

    def get(self, coupon):
        apis = {
            'list_user_coupon': self.ccoupon.list_user_coupon,
            'list': self.ccoupon.list,
            'get': self.ccoupon.get,
        }
        return apis

    def post(self, coupon):
        apis = {
            'create': self.ccoupon.create,
            'update': self.ccoupon.update,
            'delete': self.ccoupon.delete,
            'fetch': self.ccoupon.fetch,
        }
        return apis
