# -*- coding: utf-8 -*-
from planet.common.base_resource import Resource
from planet.control.CUser import CUser


class AUser(Resource):
    def __init__(self):
        self.user = CUser()

    def post(self, user):
        apis = {
            'login': self.user.login,  # 正式用户登录
            'add_address': self.user.add_useraddress,  # 添加用户地址
            'update_address': self.user.update_useraddress,  # 更新用户地址
            'login_test': self.user.login_test,  # 测试登录
            'upgrade_agent': self.user.upgrade_agent,  # 申请成为店主
            'update_user': self.user.update_user,  # 更新用户信息
            'user_sign_in': self.user.user_sign_in,  # 用户签到
            'admin_login': self.user.admin_login,  # 管理员登录
            'add_admin_by_superadmin': self.user.add_admin_by_superadmin,  # 添加管理员
            'update_admin': self.user.update_admin,  # 更新管理员信心
            'wx_login': self.user.wx_login,  # 微信登录
            'bing_telphone': self.user.bing_telphone,  # 微信登录绑定手机号
            'update_admin_password': self.user.update_admin_password,  # 修改管理员密码
            'supplizer_login': self.user.supplizer_login,  # 供应商登录
            'apply_cash': self.user.apply_cash,  # 提现申请
            'update_user_commision': self.user.update_user_commision,  # 设置个人佣金比
            'set_signin_default': self.user.set_signin_default,  # 设置默认签到规则
            'settlenment': self.user.settlenment,  # 供应商确认结算
            'create_settlenment': self.user.create_settlenment,  # 供应商确认结算创建
            # 'update': self.user.update,
            # 'destroy': self.user.destroy,
        }
        return apis

    def get(self, user):
        apis = {
            'get_inforcode': self.user.get_inforcode,  # 获取验证码
            'get_home': self.user.get_home,  # 获取个人首页
            'get_all_address': self.user.get_useraddress,  # 获取所有地址
            'get_one_address': self.user.get_one_address,  # 获取地址详情
            'check_idcode': self.user.authentication_real_name,  # 实名认证
            # 'get_profile': self.user.get_profile,
            # 'get_safecenter': self.user.get_safecenter,
            'get_identifyinginfo': self.user.get_identifyinginfo,  # 获取个人身份详情
            'get_upgrade': self.user.get_upgrade,  # 获取店主申请页 已废弃
            'get_agent_center': self.user.get_agent_center,  # 获取 店主版个人中心
            'get_agent_commission_list': self.user.get_agent_commission_list,  # 获取佣金列表
            'get_user_integral': self.user.get_user_integral,  # 获取个人积分列表
            'get_admin_list': self.user.get_admin_list,  # 获取管理员列表
            'get_wxconfig': self.user.get_wxconfig,  # 获取微信参数
            'get_discount': self.user.get_discount,  # 获取优惠中心
            'get_admin_all_type': self.user.get_admin_all_type,  # 获取管理员所有身份
            'get_admin_all_status': self.user.get_admin_all_status,  # 获取管理员所有状态
            'secret_usid': self.user.get_secret_usid,  # base64编码后的usid
            'get_bankname': self.user.get_bankname,  # 获取银行名
            'get_salesvolume_all': self.user.get_salesvolume_all,  # 获取团队销售额
            'list_user_commison': self.user.list_user_commison,  # 销售商列表(后台佣金)
            'list_fans': self.user.list_fans,  # 获取某人粉丝列表
            'get_cash_notes': self.user.get_cash_notes,  # 获取某人提现申请记录
            'get_signin_default': self.user.get_signin_default,  # 获取默认签到规则
            'get_settlenment': self.user.get_settlenment,  # 获取结算记录
        }
        return apis
