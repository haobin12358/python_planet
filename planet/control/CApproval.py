import json
import random
import re

import datetime
import uuid
from decimal import Decimal

from flask import request

from planet.common.base_service import get_session
from planet.config.enums import ApprovalStatus, ApprovalType, UserIdentityStatus, PermissionNotesType, AdminLevel, \
    AdminStatus, UserLoginTimetype, UserMediaType
from planet.common.error_response import ParamsError, SystemError, TokenError, TimeError, NotFound, AuthorityError
from planet.common.success_response import Success
from planet.common.request_handler import gennerc_log
from planet.common.params_validates import parameter_required
from planet.common.token_handler import token_required, is_admin, is_hign_level_admin
from planet.models import News

from planet.models.approval import Approval, Permission, ApprovalNotes, PermissionType, PermissionItems, \
    PermissionNotes, AdminPermission
from planet.models.user import Admin, AdminNotes, User, UserLoginTime, CashNotes, UserMedia
from planet.models.product import Products, Supplizer, ProductScene, SceneItem, ProductItems, ProductBrand, ProductSku, \
    ProductSkuValue, Items, ProductCategory
from planet.models.trade import OrderRefundApply
from planet.service.SApproval import SApproval
from planet.extensions.register_ext import db


from .BaseControl import BASEAPPROVAL


class CApproval(BASEAPPROVAL):
    def __trim_string(self, s):
        if isinstance(s, str):
            return re.sub(r'\s+', s)

        if isinstance(s, list):
            trans_list = [self.__trim_string(s_item) for s_item in s]

            return trans_list
        if isinstance(s, dict):
            tras_dict = {k: self.__trim_string(v) for k, v in s.items()}
            return tras_dict
        return s

    @get_session
    @token_required
    def add_permissionitems(self):
        """超级管理员添加权限标签"""
        if not is_hign_level_admin():
            raise AuthorityError("不是超级管理员")
        admin = Admin.query.filter_by_(ADid=request.user.id).first()
        if not admin:
            gennerc_log('get admin failed id is {0}'.format(admin.ADid))

        data = parameter_required(('piname',))
        ptn = {
            'PNid': str(uuid.uuid1()),
            'ADid': admin.ADid,
            'PNType': PermissionNotesType.pi.value
        }
        # piname = re.sub(r'\s+', data.get('ptname'))
        piname = self.__trim_string(data.get('piname'))
        if not piname:
            raise ParamsError('参数不能为空')

        pi = PermissionItems.query.filter_by_(PIname=piname).first()
        if pi:
            raise ParamsError('权限名不能重复')
        if data.get('piid'):
            pi = PermissionItems.query.filter_by_(PIid=data.get('piid'), PIstatus=1).first_('权限标签已失效')
            ptn.setdefault('PNcontent', pi.PIid)
            ptn.setdefault('PINaction', '更新权限标签 {} 为 {}'.format(pi.PIname, piname))
            pi.PIname = piname
            db.session.add(PermissionNotes.create(ptn))
            return Success('修改权限标名成功')
        pi = PermissionItems.create({
            'PIid': str(uuid.uuid1()),
            'PIname': piname,
        })
        db.session.add(pi)
        ptn.setdefault('PNcontent', pi.PIid)
        ptn.setdefault('PINaction', '创建权限标签 {} 成功'.format(piname))
        db.session.add(PermissionNotes.create(ptn))
        return Success('创建权限标签成功')

    @get_session
    @token_required
    def add_permission_type(self):
        """超级管理员增加权限类型"""
        if not is_hign_level_admin():
            raise AuthorityError("不是超级管理员")

        admin = Admin.query.filter_by_(ADid=request.user.id).first()
        if not admin:
            gennerc_log('get admin failed id is {0}'.format(admin.ADid))
            raise NotFound("该管理员已被删除")

        data = parameter_required(('ptname',))
        ptn = {
            'PNid': str(uuid.uuid1()),
            'ADid': admin.ADid,
            'PNType': PermissionNotesType.pt.value
        }
        ptname = re.sub(r'\s+', data.get('ptname'))
        if not ptname:
            raise ParamsError('ptname 不能为空')

        pt = PermissionType.query.filter_by_(PTname=ptname).first()

        if pt:
            raise ParamsError('{0} is already exist'.format(ptname))

        if data.get('ptid'):
            # 'PNcontent': data.get('piid'),
            pt = PermissionType.query.filter_by_(PTid=data.get('ptid')).first()

            if pt:
                ptn.setdefault('PNcontent', data.get('ptid'))
                ptn.setdefault('PTNaction', '修改 {} 权限类型为 {}'.format(pt.PTname, ptname))
                pt.PTname = ptname
                db.session.add(PermissionNotes.create(ptn))
                return Success('修改审批流类型名成功')

        pt_dict = {
            'PTid': str(uuid.uuid1()),
            'PTname': str(data.get('ptname')).strip()
        }
        ptn.setdefault('PNcontent', pt_dict.get('PTid'))
        ptn.setdefault('PINaction', '创建 {} 审批类型'.format(ptname))
        db.session.add(PermissionType.create(pt_dict))
        return Success('创建审批类型成功')

    @get_session
    @token_required
    def add_permission(self):
        """超级管理员给权限标签 赋予/修改权限"""
        if not is_hign_level_admin():
            raise AuthorityError("不是超级管理员")

        data = parameter_required(('piid', 'ptid', 'pelevel'))

        admin = Admin.query.filter_by_(ADid=request.user.id).first()
        if not admin:
            gennerc_log('get admin failed id is {0}'.format(admin.ADid))
            raise NotFound("该管理员已被删除")

        ptn = {
            'PNid': str(uuid.uuid1()),
            'ADid': admin.ADid,
            'PNtype': PermissionNotesType.pe.value
        }
        pt_after = PermissionType.query.filter_by_(PTid=data.get('ptid'))
        pi_after = PermissionItems.query.filter_by_(PIid=data.get('piid'))
        if not pt_after or not pi_after:
            raise ParamsError('修改的类型已被删除')

        if data.get('peid'):
            pm = Permission.query.filter_by_(PEid=data.get('peid')).first()
            pt_before = PermissionType.query.filter_by_(PTid=pm.PTid).first_('审批类型已失效')
            pi_before = PermissionItems.query.filter_by_(PIid=pm.PIid).first_('审批角色已失效')
            if pm:
                action = '更新 {4} 权限 {0} 等级 {1} 为 {5} 权限 {2} 等级 {3}'.format(
                    pt_before.PTname, pm.PELevel, pt_after.PTname, data.get('pelevel'),
                    pi_before.PIname, pi_after.PIname
                )
                pm.PELevel = data.get('pelevel')
                pm.PTid = pt_after.PTid
                ptn.setdefault('PINaction', action)
                ptn.setdefault('PNcontent', data.get('peid'))
                # 'PNcontent': data.get('peid'),
                db.session.add(PermissionNotes.create(ptn))
                return Success('权限变更成功')

            # 插入操作
            permission_instence = Permission.create({
                "PEid": str(uuid.uuid1()),
                "PIid": data.get("piid"),
                "PTid": data.get("PTid"),
                "PElevel": data.get("pelevel")
            })
            db.session.add(permission_instence)
            # ptn['ANaction'] = '创建 权限 {0} 等级 {1}'.format(
            #     pt_after.PTname, data.get("pelevel"))
            ptn.setdefault('PINaction', '创建 {2} 权限 {0} 等级 {1}'.format(
                pt_after.PTname, data.get("pelevel"), pi_after.PIname))
            ptn.setdefault('PNcontent', permission_instence.PEid)
            db.session.add(PermissionNotes.create(ptn))
            return Success('创建权限成功')

    @token_required
    def get_permission_type_list(self):
        """超级管理员查看所有权限类型list"""
        # args = request.args.to_dict()
        # page_num = args.get('page_num', 1)
        # page_size = args.get('page_size', 15)
        admin = Admin.query.filter_by_(ADid=request.user.id).first()
        if not admin:
            gennerc_log('get admin failed id is {0}'.format(admin.ADid))
            raise NotFound("该管理员已被删除")
        if admin.ADlevel == AdminLevel.super_admin:
            pt_list = PermissionType.query.filter_by_().order_by(PermissionType.createtime.desc()).all()
            for pt in pt_list:
                pm_num = Permission.query.filter_by_(PTid=pt.PTid).count()
                pt.fill('amount', pm_num)
            return Success('获取审批流类型成功', data=pt_list)
        pi_list = AdminPermission.query.filter_by_(ADid=admin.ADid).all()
        ptid_list = []
        for pi in pi_list:
            pt_sub_list = Permission.query.filter_by_(PIid=pi.PIid).all()
            ptid_list.extend([pt.PTid for pt in pt_sub_list])

        ptid_list = list(set(ptid_list))  # 去重

        pt_list = PermissionType.query.filter(
            PermissionType.PTid in ptid_list, PermissionType.isdelete == False).order_by(PermissionType.createtime.desc()).all()
        for pt in pt_list:
            pm_num = Permission.query.filter_by_(PTid=pt.PTid).count()
            pt.fill('amount', pm_num)
        return Success('获取审批流类型成功', data=pt_list)

    @token_required
    def get_permission_list(self):

        data = parameter_required(('ptid', ))
        admin = Admin.query.filter_by_(ADid=request.user.id).first()
        if not admin:
            gennerc_log('get admin failed id is {0}'.format(admin.ADid))
            raise NotFound("该管理员已被删除")
        # page_size = data.get('page_size', 15)
        # page_num = data.get('page_num', 1)
        pt = PermissionType.query.filter_by_(PTid=data.get('ptid')).first_('该审批流类型已失效')
        pm_list = Permission.query.filter_by_(
            PTid=pt.PTid).order_by(Permission.createtime.desc()).all_with_page()
        for pm in pm_list:
            pi = PermissionItems.query.filter_by_(PIid=pm.PIid).first('审批权限已被回收')
            pm.fill('piname', pi.PIname)
        return Success('获取审批权限成功')

    @token_required
    def get_permission_admin_list(self):
        """获取审批权限下的管理员列表"""
        data = parameter_required(('piid', ))
        admin = Admin.query.filter_by_(ADid=request.user.id).first()
        if not admin:
            gennerc_log('get admin failed id is {0}'.format(admin.ADid))
            raise NotFound("该管理员已被删除")
        ad_list = AdminPermission.query.filter_by_(PIid=data.get('piid')).all()
        for ad in ad_list:
            ad.fields = ['ADid', 'ADname', 'ADheader', 'createtime', 'ADtelphone', 'ADnum']
            ad.fill('adlevel', AdminLevel(ad.ADlevel).zh_value)
            ad.fill('adstatus', AdminStatus(ad.ADstatus).zh_value)
            ad.fill('adpassword', '*' * 6)
            ad_login = UserLoginTime.query.filter_by_(
                USid=ad.ADid, ULtype=UserLoginTimetype.admin.value).order_by(UserLoginTime.createtime.desc()).first()
            logintime = None
            if ad_login:
                logintime = ad_login.createtime
            ad.fill('logintime', logintime)
        return Success('获取权限管理员成功', data=ad_list)

    def get_permission_detail(self):
        """超级管理员查看单个管理员的所有权限"""
        # todo
        pass

    @token_required
    def get_dealing_approval(self):
        """管理员查看自己名下可以处理的审批流"""
        admin = Admin.query.filter_by_(ADid=request.user.id).fist_('管理员账号已被回收')

        pt_list = PermissionType.query.filter(
            PermissionType.PTid == Permission.PTid, Permission.PIid == AdminPermission.PIid,
            AdminPermission.ADid == admin.ADid, AdminPermission.isdelete == False, Permission.isdelete == False
        ).order_by(PermissionType.createtime.desc()).all()
        # pi_list = AdminPermission.query.filter_by_(ADid=admin.ADid).all()
        for pt in pt_list:
            ap_list = Approval.query.filter_by_(
                Approval.PTid == pt.PTid, Approval.AVlevel == Permission.PELevel, Permission.PTid == pt.PTid,
                Permission.PIid == AdminPermission.PIid, AdminPermission.ADid == admin.ADid,
                Approval.isdelete == False, Permission.isdelete == False, AdminPermission.isdelete == False
            ).all()
            pt.fill('approval_list', ap_list)

    def __fill_pttype(self, pt, startid, contentid):
        # todo 通过类型id 不能自动找到对应的身份和审批类容，后期修改
        if pt.PTid == 'tocash':
            # 提现操作
            # start_model = User.query.filter_by_(USid=startid).first_('用户不存在')
            content = CashNotes.query.filter_by_(CNid=contentid).first()
            # pt.fill('start', start_model)
            pt.fill('content', content)

        elif pt.PTid == 'toagent':
            # 成为代理商
            start_model = User.query.filter_by_(USid=startid).first_('用户不存在')
            umfront = UserMedia.query.filter_by_(USid=startid, UMtype=UserMediaType.umfront.value).first()
            umback = UserMedia.query.filter_by_(USid=startid, UMtype=UserMediaType.umback.value).first()
            start_model.fill('umfront', umfront['UMurl'])
            start_model.fill('umback', umback['UMurl'])
            pt.fill('start', start_model)
        elif pt.PTid == 'toshelves':
            # 商品上架
            start_model = Supplizer.query.filter_by_(SUid=startid).frist_('供应商不存在')
            content = Products.query.filter_by_(PRid=contentid).first()
            content.PRattribute = json.loads(content.PRattribute)
            content.PRremarks = json.loads(getattr(content, 'PRremarks') or '{}')
            pb = ProductBrand.query.filter_by_(PBid=content.PBid)
            # ps = ProductScene.query.filter(
            #     ProductScene.PSid == SceneItem.PSid, SceneItem.ITid == ProductItems.ITid,
            #     ProductItems.PRid == contentid).first()
            # skus = self.sproduct.get_sku({'PRid': prid})
            skus = ProductSku.query.filter_by_(PRid=contentid).all()
            sku_value_item = []
            for sku in skus:
                sku.SKUattriteDetail = json.loads(sku.SKUattriteDetail)
                sku_value_item.append(sku.SKUattriteDetail)
            sku_value_instance = ProductSkuValue.query.filter_by_({
                'PRid': contentid
            }).first()
            if not sku_value_instance:
                sku_value_item_reverse = []
                for index, name in enumerate(content.PRattribute):
                    value = list(set([attribute[index] for attribute in sku_value_item]))
                    value = sorted(value)
                    temp = {
                        'name': name,
                        'value': value
                    }
                    sku_value_item_reverse.append(temp)
            else:
                sku_value_item_reverse = []
                pskuvalue = json.loads(sku_value_instance.PSKUvalue)
                for index, value in enumerate(pskuvalue):
                    sku_value_item_reverse.append({
                        'name': content.PRattribute[index],
                        'value': value
                    })

            # item = Items.query.filter()
            categorys = ' > '.join(self.__get_category(content.PCid))
            content.fill('SkuValue', sku_value_item_reverse)
            content.fill('brand', pb)
            content.fill('skus', skus)
            content.fill('categorys', categorys)

        elif pt.PTid == 'toreturn':
            # 退货
            pass
        elif pt.PTid == 'topublish':
            # 发布评论
            start = User.query.filter_by_(USid=startid).first_('用户已被注销')
            content = News.query.filter_by_(NEid=contentid).first()
        elif pt.PTid == 'toactivite':
            # todo
            pass

    def __get_category(self, pcid, pclist=None):
        if not pclist:
            pclist = []
        if not pcid:
            return pclist
        pc = ProductCategory.query.filter_by_(PCid=pcid).first()
        # pc_list = []
        if not pc:
            return pclist
        return self.__get_category(pc.ParentPCid, pclist)


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
        # todo 修改
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
                    approval_model.AVstatus = ApprovalStatus.complate.value
            else:
                # 审批操作为拒绝 等级回退到最低级
                approval_model.AVstatus = ApprovalStatus.refuse.value
                approval_model.AVlevel = 1
                if approval_model.AVtype == ApprovalType.toagent.value:
                    s.query(User).filter(User.USid == approval_model.AVstartid).update({"USlevel": UserIdentityStatus.ordinary.value})

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
