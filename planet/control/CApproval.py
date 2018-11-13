import json
import random
import re

import datetime
import uuid
from decimal import Decimal

from flask import request
from planet.config.enums import PermissionType
from planet.common.error_response import ParamsError, SystemError, TokenError, TimeError, NotFound, AuthorityError
from planet.common.success_response import Success
from planet.common.request_handler import gennerc_log
from planet.common.params_validates import parameter_required
from planet.common.token_handler import token_required, is_admin, is_hign_level_admin

from planet.models.approval import Approval, Permission, ApprovalNotes
from planet.models.user import Admin, AdminNotes
from planet.models.product import Products
from planet.models.trade import OrderRefundApply
from planet.service.SApproval import SApproval
from planet.service.SProduct import SProducts
from planet.service.STrade import STrade

from .BaseControl import BASEAPPROVAL


class CApproval(BASEAPPROVAL):
    def __init__(self):
        self.sapproval = SApproval()

    @token_required
    def add_permission(self):
        """超级管理员给管理员赋予/修改权限"""
        if not is_hign_level_admin():
            raise AuthorityError("不是超级管理员")

        data = parameter_required(('adid', 'petype', 'pelevel'))

        with self.sapproval.auto_commit() as s:
            admin = s.query(Admin).filter_by_(ADid=data.get("adid")).first()
            if not admin:
                gennerc_log('get admin failed id is {0}'.format(data.get('adid')))
                raise NotFound("该管理员已被删除")

            an_dict = {
                'ANid': str(uuid.uuid1()),
                "ADid": data.get("adid"),
                "ANdoneid": request.user.id
            }

            if data.get("peid"):
                permission_model = s.query(Permission).filter_by_(PEid=data.get('peid')).first()
                if permission_model:
                    # 更新操作
                    acation = '更新 权限 {0} 等级 {1}'.format(
                        PermissionType(permission_model.PEtype), permission_model.PELevel)
                    permission_model.PELevel = data.get("pelevel")
                    permission_model.PEtype = data.get("petype")

                    an_dict['ANaction'] = acation + ' 为 权限 {0} 等级 {1}'.format(
                        PermissionType(data.get("petype")), data.get("pelevel"))
                    an_instance = AdminNotes.create(an_dict)
                    s.add(an_instance)
                    return Success('管理员权限变更成功')
            # 插入操作
            permission_instence = Permission.create({
                "PEid": str(uuid.uuid1()),
                "ADid": data.get("adid"),
                "PEtype": data.get("petype"),
                "PElevel": data.get("pelevel")
            })
            s.add(permission_instence)
            an_dict['ANaction'] = '创建 权限 {0} 等级 {1}'.format(
                PermissionType(data.get("petype")).name, data.get("pelevel"))
            an_instance = AdminNotes.create(an_dict)
            s.add(an_instance)
            return Success('管理员权限添加成功')

    def get_permission_list(self):
        """超级管理员查看所有权限list"""
        # todo
        pass

    def get_permission_detail(self):
        """超级管理员查看单个管理员的所有权限"""
        # todo
        pass

    def get_dealing_approval(self):
        """管理员查看自己名下可以处理的审批流"""
        # todo
        pass

    def get_submit_approval(self):
        """代理商查看自己提交的所有审批流"""
        # todo
        pass

    @token_required
    def deal_approval(self):
        """管理员处理审批流"""
        if not is_admin():
            raise AuthorityError('权限不足')
        data = parameter_required(('avid', 'anaction', 'anabo'))
        with self.sapproval.auto_commit() as s:
            admin = s.query(Admin).filter_by_(ADid=data.get("adid")).first_("该管理员已被删除")
            approval_model = s.query(Approval).filter_by_(AVid=data.get('avid')).first_('审批不存在')
            s.query(Permission).filter(
                Permission.ADid == request.user.id,
                Permission.PEtype == approval_model.AVtype,
                Permission.PELevel == approval_model.AVlevel
            ).first_('权限不足')

            if int(data.get("anaction")) == 1:
                # 审批操作是否为同意
                pm_model = s.query(Permission).filter(
                    Permission.PEtype == approval_model.AVtype,
                    Permission.PELevel == int(approval_model.AVlevel) + 1
                )
                if pm_model:
                    # 如果还有下一级审批人
                    approval_model.AVlevel += 1
                else:
                    # 没有下一级审批人了
                    approval_model.AVstatus = 10
            else:
                # 审批操作为拒绝 等级回退到最低级
                approval_model.AVstatus = -10
                approval_model.AVlevel = 1

            # 审批流水记录
            approvalnote_dict = {
                "ANid": str(uuid.uuid1()),
                "AVid": data.get("avid"),
                "AVadname": admin.ADname,
                "ADid": admin.ADid,
                "ANaction": data.get('anaction'),
                "ANabo": data.get("anabo")
            }
            apn_instance = ApprovalNotes.create(approvalnote_dict)
            s.add(apn_instance)
        return Success("审批操作完成")

    @token_required
    def cancel(self):
        """用户取消申请"""
        # todo
        pass

    @token_required
    def get_approvalnotes(self):
        """查看审批的所有流程"""
        # todo 注意增加发起记录
        pass
