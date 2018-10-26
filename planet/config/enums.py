# *- coding:utf8 *-
activity_type = {
    '0': '普通动态',
    '1': '满减',
    '2': '满赠',
    '3': '优惠券',
    '4': '砍价',
    '5': '拼团',
    '6': '单品优惠券',
    '7': '一元秒杀',
    '8': '前{0}分钟半价',
    '9': '限时抢',
    '10': 'x元x件',
}


complain_type = {
    '201': "客服态度差",
    '202': "商品质量问题",
    '203': "售后方案不合理",
    '204': "商品包装问题"
}

# ['1', '4', '5', '6', '11']
ORDER_STATUS = {  # 订单详细状态

    '0': '全部',
    '1': '待支付',
    '2': '支付成功',
    '3': '支付超时关闭（交易关闭）',
    '4': '待发货',
    '5': '待收货',
    '6': '已完成',
    '7': '已取消',
    '8': '交易失败（退货）',
    # '9': '交易完成', 和已完成重复
    '10': '待评价',  # 不要了
    '11': '退换货',
    '12': '换货(买家退回中)',
    '13': '换货(卖家发货中)',
    '14': '换货(卖家已发货)',
}


BANK_MAP = {
    "ICBC": "工商银行",
    "ABC": "农业银行",
    "BOC": "中国银行",
    "PSBC": "邮政储蓄",
    "CCB":"中国建设银行",
    "NXS": "农村信用社",
}

TASK_TYPE = {
    '0': "观看视频",
    '1': "转发商品",
    '2': "售出商品",
    '3': "售出大礼包"
}

TASK_STATUS = {
    '0': "进行中",
    '1': "已完成",
    '2': "已暂停",
    '3': "已过期",
    '4': "已失效",
}

REWARD_TYPE = {
    '0': "满减",
    '1': "佣金加成",
    '2': "无门槛",
    '3': "邀请粉丝专用券",
    '4': "开店大礼包专用"
}

icon = {
           "name": '首页',
           "icon": 'https://weidianweb.daaiti.cn/imgs/icon/home.png',
           "active_icon": 'https://weidianweb.daaiti.cn/imgs/icon/home2.png',
           "url": 'index'
       }, {
           "name": '客服',
           "icon": 'https://weidianweb.daaiti.cn/imgs/icon/info.png',
           "active_icon": 'https://weidianweb.daaiti.cn/imgs/icon/info2.png',
           "url": 'service'
       }, {
           "name": '发现',
           "icon": 'https://weidianweb.daaiti.cn/imgs/icon/search2.png',
           "active_icon": 'https://weidianweb.daaiti.cn/imgs/icon/search.png',
           "url": 'discover'
       }, {
           "name": '购物车',
           "icon": 'https://weidianweb.daaiti.cn/imgs/icon/cart2.png',
           "active_icon": 'https://weidianweb.daaiti.cn/imgs/icon/cart.png',
           "url": 'shopping'
       }, {
           "name": '我的',
           "icon": 'https://weidianweb.daaiti.cn/imgs/icon/me.png',
           "active_icon": 'https://weidianweb.daaiti.cn/imgs/icon/me2.png',
           "url": 'personal'
       }

finished_pay_status = ['2', '4', '5', '7', '9', '10', '11']

HMSkipType = {'0': '无跳转类型', '1': '专题', '2': '商品', '3': '教程', '4': '公告'}

staticimage = {
    "home": "home.png",
    "home_active": "home2.png",
    "info": "info.png",
    "info_active": "info2.png",
    "search": "search2.png",
    "search_active": "search.png",
    "cart": "cart2.png",
    "cart_active": "cart.png",
    "me": "me.png",
    "me_active": "me2.png",
    "shareimage": "shareimage.png",
}

userlevel = {'0': '普通用户', '1': '普通合伙人', '2': '中级合伙人', '3': '高级合伙人'}


ORDER_STATUS_ = {  # 订单简略状态

    '0': '全部',
    '1': '买家未付款',
    '2': '买家已付款',
    '3': '交易关闭',
    '4': '买家已付款',
    '5': '卖家已发货',
    '6': '交易完成',
    '7': '已取消',
    '8': '交易失败（退货）',
    # '9': '交易完成', 和已完成重复
    '10': '交易完成',  # 不要了
    '11': '退换货',
    '12': '退换货',
    '13': '退换货',
    '14': '退换货',
}
order_product_info_status = {0: '待发货', 1: '待收货', 2: '交易成功(未评价)', 3: '交易成功(已评价)', 4: '已签收'}  # 订单中的商品状态
OrderResend = {0: '已申请', 1: '等待买家发货', 3: '买家已发货', 3: '卖家发货中', 4: '卖家已发货', 5: '完成', 6: '拒绝申请'}
OrderResendType = {0: '退货', 1: '换货'}
