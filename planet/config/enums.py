# -*- coding: utf-8 -*-
from enum import Enum


class ProductStatus(Enum):
    """商品状态"""
    usual = 0  # 正常
    offsale = 10  # 下架


class PayType(Enum):
    """支付方式"""
    wechat_pay = 0
    alipay = 10


class Client(Enum):
    """客户端"""
    wechat = 0
    app = 10


class OrderFrom(Enum):
    """订单商品来源"""
    carts = 0
    product_info = 10

if __name__ == '__main__':
    import ipdb
    ipdb.set_trace()


