# -*- coding: utf-8 -*-
from enum import Enum


class ProductStatus(Enum):
    """商品状态"""
    usual = 0  # 正常
    auditing = 10  # 审核中
    offsale = 60  # 下架


class ProductFrom(Enum):
    """商品来源"""
    platform = 0  # 平台发布
    shop_keeper = 10  # 店主发布
    # ..其他


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


class OrderMainStatus(Enum):
    """主订单状态
    0待付款,10待发货,20待收货,30完成
    """
    wait_pay = 0
    wait_send = 10
    wait_recv = 20
    ready = 30
    cancle = -40


class OrderPartStatus(Enum):
    """订单副表状态 0正常状态, -10退货申请,-20退货中,-30已退货"""
    usual = 0
    apply_refund = -10
    refunding = -20
    already = -30


if __name__ == '__main__':
    import ipdb
    ipdb.set_trace()


