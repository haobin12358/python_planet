from flask import request

from planet.common.params_validates import parameter_required
from planet.common.success_response import Success
from planet.common.token_handler import token_required, is_admin
from planet.config.enums import UserActivationCodeStatus
from planet.models import UserActivationCode, ActivationCodeRule


class CActivationCode:
    def create_apply(self):
        """提交购买申请"""
        pass

    def get_rule(self):
        """获取规则电话地址以及下方协议以及收款信息"""
        info = ActivationCodeRule.query.filter_by_().first_()


    @token_required
    def get_user_activationcode(self):
        """获取用户拥有的激活码"""
        if not is_admin():
            usid = request.user.id
            user_act_codes = UserActivationCode.query.filter(
                UserActivationCode.isdelete == False,
                UserActivationCode.USid == usid
            ).order_by(
                UserActivationCode.createtime.desc()
            ).all_with_page()
        elif is_admin():
            data = parameter_required()
            usid = data.get('usid')
            user_act_codes = UserActivationCode.query.filter_(
                UserActivationCode.isdelete == False,
                UserActivationCode.USid == usid
            ).order_by(
                UserActivationCode.createtime.desc()
            ).all_with_page()
            # todo 管理员查看激活码
            pass
        for user_act_code in user_act_codes:
            user_act_code.fill('uacstatus_zh',
                               UserActivationCodeStatus(user_act_code.UACstatus).zh_value)

        return Success(data=user_act_codes)