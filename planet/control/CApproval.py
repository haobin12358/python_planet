import json
import random
import re

import datetime
import uuid
from decimal import Decimal

from flask import request

from planet.common.base_service import get_session
from planet.config.enums import ApprovalType, UserIdentityStatus, PermissionNotesType, AdminLevel, \
    AdminStatus, UserLoginTimetype, UserMediaType, ActivityType, ApplyStatus, ApprovalAction, ProductStatus, NewsStatus, \
    GuessNumAwardStatus, TrialCommodityStatus
from planet.common.error_response import ParamsError, SystemError, TokenError, TimeError, NotFound, AuthorityError
from planet.common.success_response import Success
from planet.common.request_handler import gennerc_log
from planet.common.params_validates import parameter_required
from planet.common.token_handler import token_required, is_admin, is_hign_level_admin, is_supplizer
from planet.models import News, GuessNumAwardApply, FreshManFirstSku, FreshManFirstApply, MagicBoxApply, TrialCommodity, \
    FreshManFirstProduct, UserWallet, UserInvitation, TrialCommodityImage, TrialCommoditySku, TrialCommoditySkuValue

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
            return re.sub(r'\s+', '', s)

        if isinstance(s, list):
            trans_list = [self.__trim_string(s_item) for s_item in s]

            return trans_list
        if isinstance(s, dict):
            tras_dict = {k: self.__trim_string(v) for k, v in s.items()}
            return tras_dict
        return s

    @get_session
    def create(self):
        data = parameter_required(('ptid', 'startid', 'avcontentid'))
        avid = self.create_approval(data.get('ptid'), data.get('startid'), data.get('avcontentid'))
        return Success('创建审批流成功', data={'avid': avid})


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
            return Success('修改权限标名成功', data={'piid':pi.PIid})
        pi = PermissionItems.create({
            'PIid': str(uuid.uuid1()),
            'PIname': piname,
        })
        db.session.add(pi)
        ptn.setdefault('PNcontent', pi.PIid)
        ptn.setdefault('PINaction', '创建权限标签 {} 成功'.format(piname))
        db.session.add(PermissionNotes.create(ptn))
        return Success('创建权限标签成功', data={'piid': pi.PIid})

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
        # ptname = re.sub(r'\s+', data.get('ptname'))
        ptname = self.__trim_string(data.get('ptname'))
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
                return Success('修改审批流类型名成功', data={'ptid': pt.PTid})

        pt_dict = {
            'PTid': str(uuid.uuid1()),
            'PTname': ptname,
        }
        if data.get('ptmodelname'):
            pt_dict.setdefault('PTmodelName', data.get('ptmodelname'))
        ptn.setdefault('PNcontent', pt_dict.get('PTid'))
        ptn.setdefault('PINaction', '创建 {} 审批类型'.format(ptname))
        db.session.add(PermissionNotes.create(ptn))
        db.session.add(PermissionType.create(pt_dict))
        return Success('创建审批类型成功', data={'ptid': pt.PTid})

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
            'PNType': PermissionNotesType.pe.value
        }
        pt_after = PermissionType.query.filter_by_(PTid=data.get('ptid')).first()
        pi_after = PermissionItems.query.filter_by_(PIid=data.get('piid')).first()
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
            "PTid": data.get("ptid"),
            "PELevel": data.get("pelevel")
        })
        db.session.add(permission_instence)
        # ptn['ANaction'] = '创建 权限 {0} 等级 {1}'.format(
        #     pt_after.PTname, data.get("pelevel"))
        ptn.setdefault('PINaction', '创建 {2} 权限 {0} 等级 {1}'.format(
            pt_after.PTname, data.get("pelevel"), pi_after.PIname))
        ptn.setdefault('PNcontent', permission_instence.PEid)
        db.session.add(PermissionNotes.create(ptn))
        return Success('创建权限成功', data={'peid': permission_instence.PEid})

    @get_session
    @token_required
    def add_adminpermission(self):
        admin = Admin.query.filter_by_(ADid=request.user.id).first_("权限被回收")
        if admin.ADlevel != AdminLevel.super_admin.value:
            raise AuthorityError('权限不够')
        data = parameter_required(('adid', 'piid'))

        check_pi = PermissionItems.query.filter_by_(PIid=data.get('piid')).first_('权限标签失效')
        for adid in data.get('adid'):
            check_admin = Admin.query.filter_by(ADid=adid).first_('管理员id异常')
            if not check_admin or not check_pi:
                raise ParamsError('参数异常')
            if data.get('adpid'):
                adp = AdminPermission.query.filter_by_(ADPid=data.get('adpid')).first()
                if adp:
                    adp.ADid = data.get('adid')
                    adp.PIid = data.get('piid')

                    return Success('修改管理员权限成功', data={'adpid': adp.ADPid})
            adp = AdminPermission.create({
                'ADPid': str(uuid.uuid1()),
                'ADid': data.get('adid'),
                'PIid': data.get('piid'),
                # 'PTid': data.get('ptid')
            })
            db.session.add(adp)
        return Success('创建管理员权限成功', data={'adpid': adp.ADPid})


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
        if admin.ADlevel == AdminLevel.super_admin.value:
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
        """获取管理员下所有审批类型"""
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
            pi = PermissionItems.query.filter_by_(PIid=pm.PIid).first_('审批权限已被回收')
            pm.fill('piname', pi.PIname)
        return Success('获取审批权限成功', data=pm_list)

    @token_required
    def get_permission_admin_list(self):
        """获取审批权限下的管理员列表"""
        data = parameter_required(('piid', ))
        admin = Admin.query.filter_by_(ADid=request.user.id).first()
        if not admin:
            gennerc_log('get admin failed id is {0}'.format(admin.ADid))
            raise NotFound("该管理员已被删除")
        ad_list = Admin.query.filter(
            AdminPermission.ADid == Admin.ADid, AdminPermission.PIid == data.get('piid')).all()
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
        """管理员查看自己名下可以处理的审批流 概览"""
        if is_admin():
            admin = Admin.query.filter_by_(ADid=request.user.id).first_('管理员账号已被回收')
            if not admin:
                gennerc_log('get admin failed id is {0}'.format(admin.ADid))
                raise NotFound("该管理员已被删除")
            # pttype = request.args.to_dict().get('pttypo')
            pt_list = PermissionType.query.filter(
                PermissionType.PTid == Permission.PTid, Permission.PIid == AdminPermission.PIid,
                AdminPermission.ADid == admin.ADid, AdminPermission.isdelete == False, Permission.isdelete == False
            ).order_by(PermissionType.createtime.desc()).all()
            # pi_list = AdminPermission.query.filter_by_(ADid=admin.ADid).all()
            for pt in pt_list:
                ap_num = Approval.query.filter(
                    Approval.PTid == pt.PTid, Approval.AVlevel == Permission.PELevel, Permission.PTid == pt.PTid,
                    Permission.PIid == AdminPermission.PIid, AdminPermission.ADid == admin.ADid,
                    Approval.isdelete == False, Permission.isdelete == False, AdminPermission.isdelete == False
                ).count()

                pt.fill('approval_num', ap_num)
        elif is_supplizer():
            sup = Supplizer.query.filter_by_(SUid=request.user.id).first_('供应商账号已回收')
            pt_list = PermissionType.query.filter(
                PermissionType.PTid == Approval.PTid, Approval.AVstartid == sup.SUid).all()
            # todo 供应商的审批类型筛选
            for pt in pt_list:
                ap_num = Approval.query.filter(
                    Approval.PTid == pt.PTid, Approval.AVlevel == Permission.PELevel, Permission.PTid == pt.PTid,
                    Permission.PIid == AdminPermission.PIid, AdminPermission.ADid == admin.ADid,
                    Approval.isdelete == False, Permission.isdelete == False, AdminPermission.isdelete == False
                ).count()

                pt.fill('approval_num', ap_num)

        return Success('获取审批流类型成功', data=pt_list)

    @token_required
    def get_approval_list(self):
        data = parameter_required(('ptid',))
        if is_admin():
            admin = Admin.query.filter_by_(ADid=request.user.id).first_()
            if not admin:
                gennerc_log('get admin failed id is {0}'.format(admin.ADid))
                raise NotFound("该管理员已被删除")

            pt = Permission.query.filter_by_(PTid=data.get('ptid')).first()
            # ptytype = ActivityType(int(data.get('pttype'))).name
            ap_list = Approval.query.filter(
                    Approval.PTid == pt.PTid, Approval.AVlevel == Permission.PELevel, Permission.PTid == pt.PTid,
                    Permission.PIid == AdminPermission.PIid, AdminPermission.ADid == admin.ADid,
                    Approval.isdelete == False, Permission.isdelete == False, AdminPermission.isdelete == False
                ).order_by(Approval.AVstatus.desc(), Approval.createtime.desc()).all()
        else:
            pt = Permission.query.filter_by_(PTid=data.get('ptid')).first_('审批类型不存在')
            sup = Supplizer.query.filter_by_(SUid=request.user.id).first_('供应商不存在')
            ap_list = Approval.query.filter_by_(AVstartid=sup.SUid).all_with_page()
        self.__fill_approval(pt, ap_list)
        page = int(data.get('page_num', 0)) or 1
        count = data.get('page_size', 15) or 15
        total_count = len(ap_list)
        if page < 1:
            page = 1
        total_page = int(total_count / count) or 1
        start = (page - 1) * count
        # end =
        if start > total_count:
            start = 0
        if total_count / (page * count) < 0:
            ap_return_list = ap_list[start:]
        else:
            ap_return_list = ap_list[start: (page * count)]
        request.page_all = total_page
        request.mount = total_count
        return Success('获取待审批列表成功', data=ap_return_list)

    # @token_required
    # def get_submit_approval(self):
    #     """供应商查看自己提交的所有审批流"""
    #     data = parameter_required(('ptid',))
    #
    #     self.__fill_approval(pt, aplist)
    #     return Success('获取审批流成功', data=aplist)

    @get_session
    @token_required
    def deal_approval(self):
        """管理员处理审批流"""
        if not is_admin():
            raise AuthorityError('权限不足')
        data = parameter_required(('avid', 'anaction', 'anabo'))
        admin = Admin.query.filter_by_(ADid=data.get("adid")).first_("该管理员已被删除")
        approval_model = Approval.query.filter_by_(AVid=data.get('avid'), AVstatus=ApplyStatus.wait_check.value).first_('审批已处理')
        Permission.query.filter(
            Permission.PIid == AdminPermission.PIid,
            AdminPermission.ADid == request.user.id,
            Permission.PTid == approval_model.PTid,
            Permission.PELevel == approval_model.AVlevel
        ).first_('权限不足')
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
        db.session.add(apn_instance)

        if int(data.get("anaction")) == ApprovalAction.agree.value:
            # 审批操作是否为同意
            pm_model = Permission.query.filter(
                Permission.PTid == approval_model.PTid,
                Permission.PELevel == int(approval_model.AVlevel) + 1
            ).first()
            if pm_model:
                # 如果还有下一级审批人
                approval_model.AVlevel = str(int(approval_model.AVlevel) + 1)
            else:
                # 没有下一级审批人了
                approval_model.AVstatus = ApplyStatus.agree.value
                self.agree_action(approval_model)
        else:
            # 审批操作为拒绝
            approval_model.AVstatus = ApplyStatus.reject.value
            # approval_model.AVlevel = 1
            self.refuse_action(approval_model, data.get('anabo'))
            # if approval_model.AVtype == ApprovalType.toagent.value:
            #     User.query.filter(User.USid == approval_model.AVstartid).update({"USlevel": UserIdentityStatus.ordinary.value})

        return Success("审批操作完成")
    @get_session
    @token_required
    def cancel(self):
        """用户取消申请"""
        if not is_supplizer():
            raise AuthorityError('权限不够')

        data = parameter_required(('avid'))
        av = Approval.query.filter_by_(AVid=data.get('avid'), AVstatus=ApplyStatus.wait_check.value).first_('审批已取消')
        if av.AVstartid != request.user.id:
            raise AuthorityError('操作账号有误')
        av.AVstatus = ApplyStatus.wait_check.value
        return Success('取消成功')

    @token_required
    def get_approvalnotes(self):
        """查看审批的所有流程"""
        if not is_admin():
            raise AuthorityError('权限不足')
        data = parameter_required(('avid',))
        an_list = ApprovalNotes.query.filter_by_(AVid=data.get('avid')).all()
        for an in an_list:
            an.fill('anaction', ApprovalAction(an.ANaction).zh_value)
        return Success('获取审批记录成功', data=an_list)

    @get_session
    @token_required
    def get_all_permissiontype(self):
        if not is_admin():
            raise AuthorityError('权限不足')

        pt_list = PermissionType.query.filter_by_().all()
        for pt in pt_list:
            pe = Permission.query.filter_by_(PTid=pt.PTid).group_by(Permission.PELevel).all()

            pt.fill('pemission', pe)

        return Success('获取所有审批流类型成功', data=pt_list)

    def __fill_publish(self, ap_list):
        """填充资讯发布"""
        for ap in ap_list:
            start = User.query.filter_by_(USid=ap.AVstartid).first()
            content = News.query.filter_by_(NEid=ap.AVcontent).first()
            if not start or not content:
                ap_list.remove(ap)
                continue
            ap.fill('start', start)
            ap.fill('content', content)

    def __fill_cash(self, ap_list):
        # 填充提现内容
        for ap in ap_list:
            start_model = User.query.filter_by_(USid=ap.AVstartid).first()
            content = CashNotes.query.filter_by_(CNid=ap.AVcontent).first()
            uw = UserWallet.query.filter_by_(USid=ap.AVstartid).first()
            if not start_model or not content or not uw:
                ap_list.remove(ap)
                continue
            content.fill('uWbalance', uw.UWbalance)
            ap.fill('start', start_model)
            ap.fill('content', content)

    def __fill_agent(self, ap_list):
        # 填充成为代理商内容
        ap_remove_list = []
        for ap in ap_list:
            start_model = User.query.filter_by_(USid=ap.AVstartid).first()

            umfront = UserMedia.query.filter_by_(USid=ap.AVstartid, UMtype=UserMediaType.umfront.value).first()
            umback = UserMedia.query.filter_by_(USid=ap.AVstartid, UMtype=UserMediaType.umback.value).first()
            if not start_model or not umback or not umfront:
                ap_remove_list.append(ap)
                continue
            start_model.fill('umfront', umfront['UMurl'])
            start_model.fill('umback', umback['UMurl'])
            ap.fill('start', start_model)
        for ap_remove in ap_remove_list:
            ap_list.remove(ap_remove)

    def __fill_shelves(self, ap_list):
        # 填充上架申请
        ap_remove_list = []
        for ap in ap_list:
            start_model = Supplizer.query.filter_by_(SUid=ap.AVstartid).first()
            content = Products.query.filter_by_(PRid=ap.AVcontent).first()
            if not start_model or not content:
                # ap_list.remove(ap)
                ap_remove_list.append(ap)
                continue
            self.__fill_product_detail(content)
            ap.fill('content', content)
            ap.fill('start', start_model)
        for ap_remove in ap_remove_list:
            ap_list.remove(ap_remove)

    def __fill_product_detail(self, product, skuid):
        # 填充商品详情
        if not product:
            return
        product.PRattribute = json.loads(product.PRattribute)
        product.PRremarks = json.loads(getattr(product, 'PRremarks') or '{}')
        pb = ProductBrand.query.filter_by_(PBid=product.PBid)
        if skuid:
            skus = ProductSku.query.filter_by_(SKUid=skuid).all()

        elif isinstance(product, FreshManFirstProduct):
            fmfs = FreshManFirstSku.query.filter_by_(FMFPid=product.FMFPid).all()
            skus = []
            for fmf in fmfs:
                sku = ProductSku.query.filter_by_(SKUid=fmf.SKUid).first()
                sku.hide('SKUprice')
                sku.fill('skuprice', fmf.SKUprice)
                skus.append(sku)
            # skus = ProductSku.query.filter(ProductSku.SKUid == FreshManFirstSku.SKUid)
        else:
            skus = ProductSku.query.filter_by_(PRid=product.PRid).all()

        sku_value_item = []
        for sku in skus:
            sku.SKUattriteDetail = json.loads(sku.SKUattriteDetail)
            sku_value_item.append(sku.SKUattriteDetail)

        sku_value_instance = ProductSkuValue.query.filter_by_({'PRid': product.PRid}).first()
        if not sku_value_instance:
            sku_value_item_reverse = []
            for index, name in enumerate(product.PRattribute):
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
                    'name': product.PRattribute[index],
                    'value': value
                })

        categorys = ' > '.join(self.__get_category(product.PCid))
        product.fill('SkuValue', sku_value_item_reverse)
        product.fill('brand', pb)
        product.fill('skus', skus)
        product.fill('categorys', categorys)

    def __fill_guessnum(self, ap_list):
        ap_remove_list = []
        for ap in ap_list:
            start_model = Supplizer.query.filter_by_(SUid=ap.AVstartid).first()
            content = GuessNumAwardApply.query.filter_by_(GNAAid=ap.AVcontent).first()
            if not start_model or not content:
                # ap_list.remove(ap)
                ap_remove_list.append(ap)
                continue
            product = Products.query.filter_by_(PRid=content.PRid).first()
            self.__fill_product_detail(product, content.SKUid)
            content.fill('product', product)
            ap.fill('start', start_model)
            ap.fill('content', content)
        for ap_remove in ap_remove_list:
            ap_list.remove(ap_remove)

    def __fill_magicbox(self, ap_list):
        ap_remove_list = []
        for ap in ap_list:
            start_model = Supplizer.query.filter_by_(SUid=ap.AVstartid).first()
            content = MagicBoxApply.query.filter_by_(MBAid=ap.AVcontent).first()
            if not start_model or not content:
                # ap_list.remove(ap)
                ap_remove_list.append(ap)
                continue
            product = Products.query.filter_by_(PRid=content.PRid).first()
            self.__fill_product_detail(product, content.SKUid)
            content.fill('product', product)
            ap.fill('start', start_model)
            ap.fill('content', content)
        for ap_remove in ap_remove_list:
            ap_list.remove(ap_remove)

    def __fill_freshmanfirstproduct(self, ap_list):
        ap_remove_list = []
        for ap in ap_list:
            start_model = Supplizer.query.filter_by_(SUid=ap.AVstartid).first()
            content = FreshManFirstProduct.query.filter_by_(FMFAid=ap.AVcontent).first()
            if not start_model or not content:
                # ap_list.remove(ap)
                ap_remove_list.append(ap)
                continue
            product = Products.query.filter_by_(PRid=content.PRid).first()
            self.__fill_product_detail(product)
            content.fill('product', product)
            ap.fill('start', start_model)
            ap.fill('content', content)
        for ap_remove in ap_remove_list:
            ap_list.remove(ap_remove)

    def __fill_trialcommodity(self, ap_list):
        ap_remove_list = []
        for ap in ap_list:
            start_model = Supplizer.query.filter_by_(SUid=ap.AVstartid).first()
            content = TrialCommodity.query.filter_by_(TCid=ap.AVcontent).first()
            if not start_model or not content:
                # ap_list.remove(ap)
                ap_remove_list.append(ap)
                continue
            # product = TrialCommodity.query.filter_by_(PRid=content.PRid).first()
            # self.__fill_product_detail(content, content.SKUid)
            # todo 试用商品字段名不对应
            content.fill("zh_remarks", "{0}天{1}元".format(content.TCdeadline, int(content.TCdeposit)))
            prbrand = ProductBrand.query.filter_by_(PBid=content.PBid).first()
            content.fill('brand', prbrand)
            content.TCattribute = json.loads(content.TCattribute)
            content.fill('zh_tcstatus', TrialCommodityStatus(content.TCstatus).zh_value)
            content.hide('CreaterId', 'PBid')
            # 商品图片
            image_list = TrialCommodityImage.query.filter_by_(TCid=ap.AVcontent, isdelete=False).all()
            [image.hide('TCid') for image in image_list]
            content.fill('image', image_list)
            # 填充sku
            skus = TrialCommoditySku.query.filter_by_(TCid=ap.AVcontent).all()
            sku_value_item = []
            for sku in skus:
                sku.SKUattriteDetail = json.loads(getattr(sku, 'SKUattriteDetail') or '[]')
                sku.SKUprice = content.TCdeposit
                sku_value_item.append(sku.SKUattriteDetail)
                content.fill('skus', skus)
            # 拼装skuvalue
            sku_value_instance = TrialCommoditySkuValue.query.filter_by_(TCid=ap.AVcontent).first()
            if not sku_value_instance:
                sku_value_item_reverse = []
                for index, name in enumerate(content.TCattribute):
                    value = list(set([attribute[index] for attribute in sku_value_item]))
                    value = sorted(value)
                    combination = {
                        'name': name,
                        'value': value
                    }
                    sku_value_item_reverse.append(combination)
            else:
                sku_value_item_reverse = []
                tskuvalue = json.loads(sku_value_instance.TSKUvalue)
                for index, value in enumerate(tskuvalue):
                    sku_value_item_reverse.append({
                        'name': content.TCattribute[index],
                        'value': value
                    })

            content.fill('skuvalue', sku_value_item_reverse)
            # content.fill('product', content)
            ap.fill('start', start_model)
            ap.fill('content', content)
        for ap_remove in ap_remove_list:
            ap_list.remove(ap_remove)

    def __fill_approval(self, pt, ap_list):
        if pt.PTid == 'tocash':
            self.__fill_cash(ap_list)
        elif pt.PTid == 'toagent':
            self.__fill_agent(ap_list)
        elif pt.PTid == 'toshelves':
            self.__fill_shelves(ap_list)
        elif pt.PTid == 'topublish':
            self.__fill_publish(ap_list)
        elif pt.PTid == 'toguessnum':
            self.__fill_guessnum(ap_list)
        elif pt.PTid == 'tomagicbox':
            self.__fill_magicbox(ap_list)
        elif pt.PTid == 'tofreshmanfirstproduct':
            self.__fill_freshmanfirstproduct(ap_list)
        elif pt.PTid == 'totrialcommodity':
            self.__fill_trialcommodity(ap_list)
        elif pt.PTid == 'toreturn':
            # todo 退货申请目前没有图
            raise ParamsError('退货申请前往订单页面实现')
        else:
            raise ParamsError('参数异常， 请检查审批类型是否被删除。如果新增了审批类型，请联系开发实现后续逻辑')

    def agree_action(self, approval_model):
        if not approval_model:
            return
        if approval_model.PTid == 'tocash':
            self.agree_cash(approval_model)
        elif approval_model.PTid == 'toagent':
            self.agree_agent(approval_model)
        elif approval_model.PTid == 'toshelves':
            self.agree_shelves(approval_model)
        elif approval_model.PTid == 'topublish':
            self.agree_publish(approval_model)
        elif approval_model.PTid == 'toguessnum':
            self.agree_guessnum(approval_model)
        elif approval_model.PTid == 'tomagicbox':
            self.agree_magicbox(approval_model)
        elif approval_model.PTid == 'tofreshmanfirstproduct':
            self.agree_freshmanfirstproduct(approval_model)
        elif approval_model.PTid == 'totrialcommodity':
            self.agree_trialcommodity(approval_model)
        elif approval_model.PTid == 'toreturn':
            # todo 退货申请目前没有图
            # return ParamsError('退货申请前往订单页面实现')
            pass
        else:
            return ParamsError('参数异常，请检查审批类型是否被删除。如果新增了审批类型，请联系开发实现后续逻辑')

    def refuse_action(self, approval_model, refuse_abo):
        if not approval_model:
            return
        if approval_model.PTid == 'tocash':
            self.refuse_cash(approval_model, refuse_abo)
        elif approval_model.PTid == 'toagent':
            self.refuse_agent(approval_model, refuse_abo)
        elif approval_model.PTid == 'toshelves':
            self.refuse_shelves(approval_model, refuse_abo)
        elif approval_model.PTid == 'topublish':
            self.refuse_publish(approval_model, refuse_abo)
        elif approval_model.PTid == 'toguessnum':
            self.refuse_guessnum(approval_model, refuse_abo)
        elif approval_model.PTid == 'tomagicbox':
            self.refuse_magicbox(approval_model, refuse_abo)
        elif approval_model.PTid == 'tofreshmanfirstproduct':
            self.refuse_freshmanfirstproduct(approval_model, refuse_abo)
        elif approval_model.PTid == 'totrialcommodity':
            self.refuse_trialcommodity(approval_model, refuse_abo)
        elif approval_model.PTid == 'toreturn':
            # todo 退货申请目前没有图
            # return ParamsError('退货申请前往订单页面实现')
            pass
        else:
            return ParamsError('参数异常，请检查审批类型是否被删除。如果新增了审批类型，请联系开发实现后续逻辑')

    def agree_cash(self, approval_model):
        if not approval_model:
            return
        cn = CashNotes.query.filter_by_(CNid=approval_model.AVcontent).first()
        uw = UserWallet.query.filter_by_(USid=approval_model.AVstartid).first()
        if not cn or not uw:
            raise SystemError('提现数据异常,请处理')
        cn.CNstatus = ApprovalAction.agree.value
        uw.UWbalance = float('%.2f' %(uw.UWbalance - cn.CNcashNum))

    def refuse_cash(self, approval_model, refuse_abo):
        if not approval_model:
            return
        cn = CashNotes.query.filter_by_(CNid=approval_model.AVcontent).first()
        if not cn:
            raise SystemError('提现数据异常,请处理')
        cn.CNstatus = ApprovalAction.refuse.value
        cn.CNrejectReason = refuse_abo

    def agree_agent(self, approval_model):
        user = User.query.filter_by_(USid=approval_model.AVstartid).first_('数据异常')
        user.USlevel = UserIdentityStatus.agent.value
        uw = UserWallet.query.filter_by_(USid=user.USid).first()
        if not uw:
            db.session.add(UserWallet.create({
                'UWid': str(uuid.uuid1()),
                'USid': user.USid,
                'UWbalance': 0,
                'UWtotal': 0
            }))
        # todo 增加用户成为代理商之前邀请的未成为其他代理商或其他代理商粉丝的用户为自己的粉丝
        fens_list = UserInvitation.query.filter_by_(USInviter=user.USid).all()
        for fens in fens_list:
            fens.isdelete = True
            fen_model = User.query.filter_by_(USid=fens.USInvited).first()
            if not fen_model or fen_model.USlevel != UserIdentityStatus.ordinary.value or fen_model.USsupper1:

                continue
            fen_model.USsupper1 = user.USid
            if user.USsupper1:
                fen_model.USsupper2 = user.USsupper1

    def refuse_agent(self, approval_model, refuse_abo):
        user = User.query.filter_by_(USid=approval_model.AVstartid).first_('成为代理商审批流数据异常')
        user.USlevel = UserIdentityStatus.ordinary.value

    def agree_shelves(self, approval_model):
        # sup = Supplizer.query.filter_by_(SUid=approval_model.AVstartid).first_('商品上架数据异常')
        product = Products.query.filter_by_(PRid=approval_model.AVcontent).first_('商品已被删除')
        product.PRstatus = ProductStatus.usual.value

    def refuse_shelves(self, approval_model, refuse_abo):
        product = Products.query.filter_by_(PRid=approval_model.AVcontent).first_('商品已被删除')
        product.PRstatus = ProductStatus.reject.value

    def agree_publish(self, approval_model):
        news = News.query.filter_by_(NEid=approval_model.AVcontent).first_('资讯已被删除')
        news.NEstatus = NewsStatus.usual.value

    def refuse_publish(self, approval_model, refuse_abo):
        news = News.query.filter_by_(NEid=approval_model.AVcontent).first_('资讯已被删除')
        news.NEstatus = NewsStatus.refuse.value

    def agree_guessnum(self, approval_model):
        gnaa = GuessNumAwardApply.query.filter_by_(GNAAid=approval_model.AVcontent).first_('猜数字商品申请数据异常')
        gnaa.GNAAstatus = ApplyStatus.agree.value
        gnaa_other = GuessNumAwardApply.query.filter(
            GuessNumAwardApply.GNAAid != gnaa.GNAAid,
            GuessNumAwardApply.GNAAstarttime == gnaa.GNAAstarttime,
            GuessNumAwardApply.GNAAendtime == gnaa.GNAAendtime,
            GuessNumAwardApply.isdelete == False
        ).all()
        for other in gnaa_other:
            other.GNAAstatus = ApplyStatus.reject.value
            other.GNAArejectReason = '您的商品未被抽中为{0}这一天的奖品'.format(gnaa.GNAAstarttime)

    def refuse_guessnum(self, approval_model, refuse_abo):
        gnaa = GuessNumAwardApply.query.filter_by_(GNAAid=approval_model.AVcontent).first_('猜数字商品申请数据异常')
        gnaa.GNAAstatus = ApplyStatus.reject.value
        gnaa.GNAArejectReason = refuse_abo

    def agree_magicbox(self, approval_model):
        mba = MagicBoxApply.query.filter_by_(MBAid=approval_model.AVcontent).first_('魔盒商品申请数据异常')
        mba.MBAstatus = ApplyStatus.agree.value
        mba_other = MagicBoxApply.query.filter(
            MagicBoxApply.MBAid != mba.MBAid,
            MagicBoxApply.MBAstarttime == mba.MBAstarttime,
            MagicBoxApply.MBAendtime == mba.MBAendtime
        ).all()
        for other in mba_other:
            other.MBAstatus = ApplyStatus.reject.value
            other.MBArejectReason = '您的商品未被抽中为{0}这一天的奖品'.format(mba.MBAstarttime)

    def refuse_magicbox(self, approval_model, refuse_abo):
        mba = MagicBoxApply.query.filter_by_(MBAid=approval_model.AVcontent).first_('魔盒商品申请数据异常')
        mba.MBAstatus = ApplyStatus.reject.value
        mba.MBArejectReason = refuse_abo

    def agree_freshmanfirstproduct(self, approval_model):
        ffa = FreshManFirstApply.query.filter_by_(FMFAid=approval_model.AVcontent).first_('新人商品申请数据异常')
        ffa.FMFAstatus = ApplyStatus.agree.value

    def refuse_freshmanfirstproduct(self, approval_model, refuse_abo):
        ffa = FreshManFirstApply.query.filter_by_(FMFAid=approval_model.AVcontent).first_('新人商品申请数据异常')
        ffa.FMFAstatus = ApplyStatus.reject.value
        ffa.FMFArejectReson = refuse_abo

    def agree_trialcommodity(self, approval_model):
        tc = TrialCommodity.query.filter_by_(TCid=approval_model.AVcontent).first_('试用商品申请数据异常')
        tc.TCstatus = TrialCommodityStatus.upper.value

    def refuse_trialcommodity(self, approval_model, refuse_abo):
        tc = TrialCommodity.query.filter_by_(TCid=approval_model.AVcontent).first_('试用商品申请数据异常')
        tc.TCstatus = TrialCommodityStatus.reject.value

    def __get_category(self, pcid, pclist=None):
        if not pclist:
            pclist = []
        if not pcid:
            return pclist
        pc = ProductCategory.query.filter_by_(PCid=pcid).first()
        # pc_list = []
        if not pc:
            return pclist
        pclist.append(pc.PCname)
        return self.__get_category(pc.ParentPCid, pclist)