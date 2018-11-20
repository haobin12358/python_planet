# -*- coding: utf-8 -*-
from .base_enum import Enum


class ProductStatus(Enum):
    """商品状态"""
    usual = (0, '正常')
    auditing = (10, '审核中')
    off_shelves = (60, '下架')
    all = None


class ProductFrom(Enum):
    """商品来源"""
    platform = (0, '平台')
    shop_keeper = 10, '店主'
    # ..其他


class ProductBrandStatus(Enum):
    """品牌状态"""
    upper = 0, '上架'
    off_shelves = 10, '下架'


class PayType(Enum):
    """{0: '微信支付', 10: 支付宝}"""
    wechat_pay = 0, '微信支付'
    alipay = 10, '支付宝'


class Client(Enum):
    """客户端"""
    wechat = 0, '微信'
    app = 10, 'app'


# 订单
class OrderFrom(Enum):
    """订单商品来源"""
    carts = 0, '购物车'
    product_info = 10, '商品详情'


class OrderMainStatus(Enum):
    """买家主订单状态
    """
    wait_pay = 0, '待支付'
    wait_send = 10, '待发货'
    wait_recv = 20, '待收货'
    wait_comment = 35, '待评价',
    ready = 30, '已完成'
    cancle = -40, '已取消'


class OrderEvaluationScore(Enum):
    """订单评分"""
    fine = 5, '非常好'
    good = 4, '好'
    general = 3, '一般'
    bad = 2, '差'
    worst = 1, '非常差'


class OrderRefundApplyStatus(Enum):
    cancle = -20, '取消'
    reject = -10, '拒绝'
    wait_check = 0, '未审核'
    agree = 10, '同意'


class OrderRefundORAstate(Enum):
    goods_money = 0, '退货退款'
    only_money = 10, '仅退款'


class ORAproductStatus(Enum):
    """退货申请时商品状态0已收货, 10 未收货"""
    already_recv = 0, '已收货'
    not_recv = 10, '未收货'


class ItemType(Enum):
    """标签类型{0: 商品, 10:资讯, 20:优惠券, 40 品牌标签}"""
    product = 0, '商品'
    news = 10, '资讯'
    coupon = 20, '优惠券'
    brand = 40, '品牌'


class LogisticsSearchStatus(Enum):
    """物流状态"""
    # :polling: 监控中，shutdown: 结束，abort: 中止，updateall：重新推送, 此
    # 为快递100参数,不用
    polling = '监控中'
    shutdown = '结束'
    abort = '终止'
    updateall = '重新推送'


class LogisticsSignStatus(Enum):
    """物流签收状态"""
    #  1.在途中 2.正在派件 3.已签收 4.派送失败
    wait_collect = 0, '等待揽收'  # 等待揽收
    on_the_way = 1, '在途中'
    sending = 2, '正在派件' # 正在派件
    already_signed = 3, '已签收'  # 已签收
    send_fail = 4, '配送失败'  # 配送失败
    error = 200, '其他异常'


class ApprovalType(Enum):
    """审批流状态"""
    toagent = 1
    tosell = 2
    toreturn = 3
    tocash = 4
    topublish = 5


class PermissionType(Enum):
    """审批人类型"""
    #  1: 成为代理商审批 2:商品上架审批 3:订单退换货审批, 4: 提现审批 5: 用户资讯发布审批
    toagent = 1
    toshelves = 2
    toreturn = 3
    tocash = 4
    topublish = 5


class NewsStatus(Enum):
    """资讯状态"""
    usual = (1, '上架中')  # 上架
    auditing = 2  # 审核中
    refuse = 0  # 下架


# user
class UserSearchHistoryType(Enum):
    """搜索记录类型 0 商品, 10 圈子"""
    product = 0
    news = 10


class UserIntegralType(Enum):
    all = None
    income = 1
    expenditure = 2


class AdminLevel(Enum):
    super_admin = 1, '超级管理员'
    common_admin = 2, '普通管理员'
    agent = 3, '代理商'


class AdminStatus(Enum):
    normal = 0, '正常'
    frozen = 1, '已冻结'
    deleted = 2, '已删除'


class UserIntegralAction(Enum):
    signin = 1, '签到'
    consumption = 2, '积分消费'


class AdminAction(Enum):
    ADname = '用户名'
    ADpassword = '密码'
    ADheader = '头像'
    ADlevel = '用户等级'
    ADstatus = '用户状态'


if __name__ == '__main__':
    print(UserSearchHistoryType.news.value)
    # import




