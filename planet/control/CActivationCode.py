import json
import random
import re
import string
import uuid

from flask import request

from planet.common.error_response import ParamsError, SystemError
from planet.common.params_validates import parameter_required
from planet.common.success_response import Success
from planet.common.token_handler import token_required, is_admin
from planet.config.enums import UserActivationCodeStatus
from planet.extensions.register_ext import db
from planet.models import UserActivationCode, ActivationCodeRule, ActivationCodeApply


class CActivationCode:
    @token_required
    def create_apply(self):
        """提交购买申请"""
        data = parameter_required(('acabankname', 'acabanksn', 'acaname', 'vouchers'))
        acabankname = data.get('acabankname')
        acabanksn = data.get('acabanksn')
        if len(acabanksn) < 10 or len(acabanksn) > 30:
            raise ParamsError('卡号错误')
        if re.findall('\D', acabanksn):
            raise ParamsError('卡号错误')
        acaname = data.get('acaname')
        vouchers = data.get('vouchers')
        if not vouchers or (not isinstance(vouchers, list)) or (len(vouchers) > 4):
            raise ParamsError('凭证有误')
        with db.auto_commit():
            apply = ActivationCodeApply.create({
                'ACAid': str(uuid.uuid1()),
                'USid': request.user.id,
                'ACAname': acaname,
                'ACAbankSn': acabanksn,
                'ACAbankname': acabankname,
                'ACAvouchers': json.dumps(vouchers)
            })
            db.session.add(apply)
        return Success('提交成功')

    def get_rule(self):
        """获取规则电话地址以及下方协议以及收款信息"""
        info = ActivationCodeRule.query.filter_by_(ACRisShow=True).first_()
        return Success(data=info)

    def agree_apply(self):
        pass

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

    def _generate_activaty_code(self, num=10):
        """生成激活码"""
        code_list = []
        lowercase = string.ascii_lowercase
        count = 0
        while len(code_list) < num:
            if count > 10:
                raise SystemError('激活码库存不足')
            code = ''.join(random.choice(lowercase) for _ in range(2)) + ''.join(str(random.randint(0, 9)) for _ in range(5))
            # 是否与已有重复
            is_exists = UserActivationCode.query.filter_by_({
                'UACcode': code,
                'UACstatus': UserActivationCodeStatus.wait_use.value
            }).first()
            if not is_exists:
                code_list.append(code)
            else:
                count += 1
        return code_list




