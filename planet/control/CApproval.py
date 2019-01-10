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
    GuessNumAwardStatus, TrialCommodityStatus, ApplyFrom, SupplizerSettementStatus
from planet.common.error_response import ParamsError, SystemError, TokenError, TimeError, NotFound, AuthorityError
from planet.common.success_response import Success
from planet.common.request_handler import gennerc_log
from planet.common.params_validates import parameter_required
from planet.common.token_handler import token_required, is_admin, is_hign_level_admin, is_supplizer
from planet.models import News, GuessNumAwardApply, FreshManFirstSku, FreshManFirstApply, MagicBoxApply, TrialCommodity, \
    FreshManFirstProduct, UserWallet, UserInvitation, TrialCommodityImage, TrialCommoditySku, TrialCommoditySkuValue, \
    ActivationCodeApply, UserActivationCode, OutStock, SettlenmentApply, SupplizerSettlement

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

        # data = parameter_required(('piid', 'ptid', 'pelevel'))
        data = parameter_required(('piid', 'ptid',))

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
        pelevel_model = Permission.query.filter_by_(PTid=data.get('ptid')).order_by(Permission.PELevel.desc()).first()
        if not pelevel_model:
            pelevel = 0
        else:
            pelevel = pelevel_model.PELevel + 1
        # 插入操作
        permission_instence = Permission.create({
            "PEid": str(uuid.uuid1()),
            "PIid": data.get("piid"),
            "PTid": data.get("ptid"),
            "PELevel": pelevel
        })
        db.session.add(permission_instence)
        # ptn['ANaction'] = '创建 权限 {0} 等级 {1}'.format(
        #     pt_after.PTname, data.get("pelevel"))
        ptn.setdefault('PINaction', '创建 {2} 权限 {0} 等级 {1}'.format(
            pt_after.PTname, pelevel, pi_after.PIname))
        ptn.setdefault('PNcontent', permission_instence.PEid)
        db.session.add(PermissionNotes.create(ptn))
        return Success('创建权限成功', data={'peid': permission_instence.PEid})

    @get_session
    @token_required
    def add_adminpermission(self):
        if not is_hign_level_admin():
            raise AuthorityError("不是超级管理员")

        admin = Admin.query.filter_by_(ADid=request.user.id).first_("权限被回收")
        if admin.ADlevel != AdminLevel.super_admin.value:
            raise AuthorityError('权限不够')
        data = parameter_required(('piid',))

        check_pi = PermissionItems.query.filter_by_(PIid=data.get('piid')).first_('权限标签失效')
        adid_list = data.get('adid', [])
        for adid in adid_list:
            check_admin = Admin.query.filter_by(ADid=adid).first_('管理员id异常')
            if not check_admin or not check_pi:
                raise ParamsError('参数异常')

            adp = AdminPermission.query.filter_by_(ADid=adid, PIid=data.get('piid')).first()
            if adp:
                continue
            adp = AdminPermission.create({
                'ADPid': str(uuid.uuid1()),
                'ADid': adid,
                'PIid': data.get('piid'),
                # 'PTid': data.get('ptid')
            })
            db.session.add(adp)
        # 校验是否有被删除的管理员
        check_adp_list = AdminPermission.query.filter_by_(PIid=data.get('piid')).all()
        for check_adp in check_adp_list:
            if check_adp.ADid not in adid_list:
               check_adp.isdelete = True

        return Success('创建管理员权限成功')

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
            AdminPermission.isdelete == False, Admin.isdelete == False,
            AdminPermission.ADid == Admin.ADid, AdminPermission.PIid == data.get('piid')).all()
        for ad in ad_list:
            ad.fields = ['ADid', 'ADname', 'ADheader', 'createtime', 'ADtelphone', 'ADnum']
            ad.fill('adlevel', AdminLevel(ad.ADlevel).zh_value)
            ad.fill('adstatus', AdminStatus(ad.ADstatus).zh_value)
            ad.fill('adpassword', '*' * 6)
            adp = AdminPermission.query.filter_by_(ADid=ad.ADid, PIid=data.get('piid')).first()
            ad.fill('adpid', adp.ADPid)
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
                AdminPermission.ADid == admin.ADid, PermissionType.isdelete == False,
                AdminPermission.isdelete == False, Permission.isdelete == False
            ).order_by(PermissionType.createtime.desc()).all()
            # pi_list = AdminPermission.query.filter_by_(ADid=admin.ADid).all()
            for pt in pt_list:
                ap_num = Approval.query.filter(
                    Approval.PTid == pt.PTid, Approval.AVlevel == Permission.PELevel, Permission.PTid == pt.PTid,
                    Permission.PIid == AdminPermission.PIid, AdminPermission.ADid == admin.ADid,
                    Approval.AVstatus == ApplyStatus.wait_check.value,
                    Approval.isdelete == False, Permission.isdelete == False, AdminPermission.isdelete == False
                ).count()

                # 退货申请 异常处理
                if pt.PTid == 'toreturn':
                    ap_num = OrderRefundApply.query.filter_by_(ORAstatus=ApplyStatus.wait_check.value).count()
                pt.fill('approval_num', ap_num)
        elif is_supplizer():
            sup = Supplizer.query.filter_by_(SUid=request.user.id).first_('供应商账号已回收')
            pt_list = PermissionType.query.filter(
                PermissionType.PTid == Approval.PTid, Approval.AVstartid == sup.SUid,
                Approval.AVstatus == ApplyStatus.wait_check.value,
                PermissionType.isdelete == False, Approval.isdelete == False
            ).all()
            # todo 供应商的审批类型筛选
            for pt in pt_list:
                ap_num = Approval.query.filter(
                    Approval.AVstartid == sup.SUid,
                    Approval.PTid == pt.PTid,
                    Approval.isdelete == False
                ).count()

                pt.fill('approval_num', ap_num)
        else:
            pt_list = []

        return Success('获取审批流类型成功', data=pt_list)

    @token_required
    def get_approval_list(self):
        data = parameter_required(('ptid',))
        filter_starttime, filter_endtime = data.get('starttime', '2018-12-01'), data.get('endtime', '2100-01-01')
        avstatus = data.get('avstatus', "")
        gennerc_log('get avstatus {0} '.format(avstatus))
        if avstatus and avstatus != 'all':
            avstatus = getattr(ApplyStatus, data.get('avstatus'), None)
        else:
            avstatus = None

        if is_admin():
            admin = Admin.query.filter_by_(ADid=request.user.id).first_()
            if not admin:
                gennerc_log('get admin failed id is {0}'.format(request.user.id))
                raise NotFound("该管理员已被删除")

            pt = PermissionType.query.filter_by_(PTid=data.get('ptid')).first()
            # ptytype = ActivityType(int(data.get('pttype'))).name
            ap_querry = Approval.query.filter(
                Approval.PTid == pt.PTid, Approval.AVlevel == Permission.PELevel, Permission.PTid == Approval.PTid,
                Permission.PIid == AdminPermission.PIid, AdminPermission.ADid == admin.ADid,
                Approval.isdelete == False, Permission.isdelete == False, AdminPermission.isdelete == False,
            )
            # import ipdb
            # ipdb.set_trace()
            if avstatus is not None:
                gennerc_log('sql avstatus = {0}'.format(avstatus.value))
                ap_querry = ap_querry.filter(Approval.AVstatus == avstatus.value)

            # 四个活动可通过申请时间筛选
            if pt.PTid == 'tomagicbox':
                ap_list = ap_querry.outerjoin(MagicBoxApply, MagicBoxApply.MBAid == Approval.AVcontent
                                              ).filter_(MagicBoxApply.MBAstarttime >= filter_starttime,
                                                        MagicBoxApply.MBAstarttime <= filter_endtime
                                                        ).order_by(Approval.AVstatus.desc(),
                                                                   MagicBoxApply.MBAstarttime.desc()).all()
            elif pt.PTid == 'toguessnum':
                ap_list = ap_querry.outerjoin(GuessNumAwardApply, GuessNumAwardApply.GNAAid == Approval.AVcontent
                                              ).filter_(GuessNumAwardApply.GNAAstarttime >= filter_starttime,
                                                        GuessNumAwardApply.GNAAstarttime <= filter_endtime
                                                        ).order_by(Approval.AVstatus.desc(),
                                                                   GuessNumAwardApply.GNAAstarttime.desc()).all()
            elif pt.PTid == 'totrialcommodity':
                ap_list = ap_querry.outerjoin(TrialCommodity, TrialCommodity.TCid == Approval.AVcontent
                                              ).filter(TrialCommodity.ApplyStartTime >= filter_starttime,
                                                       TrialCommodity.AgreeEndTime <= filter_endtime
                                                       ).order_by(Approval.AVstatus.desc(),
                                                                  TrialCommodity.ApplyStartTime.desc()).all()
            elif pt.PTid == 'tofreshmanfirstproduct':
                ap_list = ap_querry.outerjoin(FreshManFirstApply, FreshManFirstApply.FMFAid == Approval.AVcontent
                                              ).filter(FreshManFirstApply.FMFAstartTime >= filter_starttime,
                                                       FreshManFirstApply.FMFAendTime <= filter_endtime
                                                       ).order_by(Approval.AVstatus.desc(),
                                                                  FreshManFirstApply.FMFAstartTime.desc()).all()

            else:
                # ap_list = ap_querry.order_by(Approval.AVstatus.desc(), Approval.createtime.desc()).all()
                # import ipdb
                # ipdb.set_trace()
                ap_list = ap_querry.order_by(Approval.AVstatus.desc(), Approval.createtime.desc()).all()
        else:
            pt = PermissionType.query.filter_by_(PTid=data.get('ptid')).first_('审批类型不存在')
            sup = Supplizer.query.filter_by_(SUid=request.user.id).first_('供应商不存在')
            ap_list = Approval.query.filter_by_(AVstartid=sup.SUid).all_with_page()
        res = []
        for ap in ap_list:
            if not ap.AVstartdetail:
                continue
            ap.hide('AVcontentdetail', 'AVstartdetail')
            content = ap.AVcontentdetail or 'null'
            start = ap.AVstartdetail or 'null'
            ap.fill('content', json.loads(content))
            ap.fill('start', json.loads(start))
            ap.add('createtime')
            res.append(ap)

        return Success('获取待审批列表成功', data=res)

    @get_session
    @token_required
    def deal_approval(self):
        """管理员处理审批流"""
        if not is_admin():
            raise AuthorityError('权限不足')
        data = parameter_required(('avid', 'anaction', 'anabo'))
        admin = Admin.query.filter_by_(ADid=request.user.id).first_("该管理员已被删除")
        approval_model = Approval.query.filter_by_(AVid=data.get('avid'), AVstatus=ApplyStatus.wait_check.value).first_('审批已处理')
        Permission.query.filter(
            Permission.isdelete == False, AdminPermission.isdelete == False,
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
                Permission.isdelete == False,
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

            self.refuse_action(approval_model, data.get('anabo'))

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
        an_list = ApprovalNotes.query.filter_by_(AVid=data.get('avid')).order_by(ApprovalNotes.createtime).all()
        for an in an_list:
            an.fill('anaction', ApprovalAction(an.ANaction).zh_value)
        return Success('获取审批记录成功', data=an_list)

    @token_required
    def get_permissionitem(self):
        pt_list = PermissionType.query.filter_by_().all()
        for pt in pt_list:
            pi_list = PermissionItems.query.filter(
                PermissionItems.PIid == Permission.PIid, Permission.PTid == pt.PTid,
                Permission.isdelete == False, PermissionItems.isdelete == False
            ).all()
            for pi in pi_list:
                pe = Permission.query.filter_by_(PIid=pi.PIid, PTid=pt.PTid).first()
                if pe:
                    pi.fill('pelevel', pe.PELevel)
                    pi.fill('peid', pe.PEid)

                adp_list = AdminPermission.query.filter_by_(PIid=pi.PIid).all()
                pi.fill('adp_list', [adp.ADPid for adp in adp_list])

            pt.fill('pi', pi_list)
        return Success('获取所有标签成功', pt_list)

    @get_session
    @token_required
    def get_all_permissiontype(self):
        if not is_admin():
            raise AuthorityError('权限不足')

        pt_list = PermissionType.query.filter_by_().all()
        for pt in pt_list:
            pe_level_list = Permission.query.filter_by_(PTid=pt.PTid).group_by(Permission.PELevel).all()
            pe_list = []
            # ad_list = []
            for pe in pe_level_list:
                pe_item_list = Permission.query.filter_by_(PELevel=pe.PELevel).all()
                for pe_item in pe_item_list:
                    pi = PermissionItems.query.filter_by_(PIid=pe_item.PIid).first()

                    if pi:
                        pe_item.fill('piname', pi.PIname)
                pe_list.append({'pelevel': pe.PELevel, 'permission': pe_item_list})

            pt.fill('pemission', pe_list)

        return Success('获取所有审批流类型成功', data=pt_list)

    @get_session
    @token_required
    def get_permissiontype(self):
        data = parameter_required(('ptid', ))
        pt = PermissionType.query.filter_by_(PTid=data.get('ptid')).first_('参数异常')
        pe_level_list = Permission.query.filter_by_(PTid=pt.PTid).group_by(Permission.PELevel).all()
        pe_list = []
        pe_level_list = [pelevel.PELevel for pelevel in pe_level_list]

        for pe_level in pe_level_list:
            pe_item_list = Permission.query.filter_by_(PELevel=pe_level, PTid=data.get('ptid')).all()
            for pe_item in pe_item_list:
                pi = PermissionItems.query.filter_by_(PIid=pe_item.PIid).first()
                if pi:
                    name = pi.PIname
                    pe_item.fill('piname', name)
            pe_list.append({'pe_level': pe_level, 'permission': pe_item_list})

        pi_list = PermissionItems.query.filter(
            PermissionItems.isdelete == False, Permission.isdelete == False,
            PermissionItems.PIid == Permission.PIid, Permission.PTid == data.get('ptid')).all()
        for pi in pi_list:
            pe = Permission.query.filter_by_(PIid=pi.PIid, PTid=pt.PTid).first()
            if pe:
                pi.fill('pelevel', pe.PELevel)
                pi.fill('peid', pe.PEid)

            ad_list = Admin.query.filter(
                Admin.isdelete == False, AdminPermission.isdelete == False,
                AdminPermission.ADid == Admin.ADid, AdminPermission.PIid == pi.PIid).all()
            for ad in ad_list:
                ad.fields = ['ADid', 'ADname', 'ADheader', 'createtime', 'ADtelphone', 'ADnum']
                ad.fill('adlevel', AdminLevel(ad.ADlevel).zh_value)
                ad.fill('adstatus', AdminStatus(ad.ADstatus).zh_value)
                ad.fill('adpassword', '*' * 6)
                adp = AdminPermission.query.filter_by_(ADid=ad.ADid, PIid=data.get('piid')).first()
                ad.fill('adpid', adp.ADPid)
                ad_login = UserLoginTime.query.filter_by_(
                    USid=ad.ADid, ULtype=UserLoginTimetype.admin.value).order_by(
                    UserLoginTime.createtime.desc()).first()
                logintime = None
                if ad_login:
                    logintime = ad_login.createtime
                ad.fill('logintime', logintime)
            pi.fill('admin', ad_list)

        return Success('获取审批类型详情成功', data={'permission': pe_list, 'permissionitem': pi_list})

    @get_session
    @token_required
    def add_pi_and_pe_and_ap(self):
        if not is_hign_level_admin():
            raise AuthorityError("不是超级管理员")
        admin = Admin.query.filter_by_(ADid=request.user.id).first_('管理员权限被回收')
        if admin.ADlevel != AdminLevel.super_admin.value:
            raise AuthorityError('权限已被回收')

        data = parameter_required(('piname', 'ptid', 'ad_list'))
        pt = PermissionType.query.filter_by_(PTid=data.get('ptid')).first_('审批类型已失效')
        ad_list = data.get('ad_list')
        if not isinstance(ad_list, list):
            raise ParamsError('管理员添加异常')
        piname = self.__trim_string(data.get('piname'))
        pi = PermissionItems.query.filter_by_(PIname=piname).first()

        if not pi:
            pi = PermissionItems.create({'PIname': piname, 'PIid': str(uuid.uuid1())})
            ptn_pi = {
                'PNid': str(uuid.uuid1()),
                'ADid': admin.ADid,
                'PNcontent': pi.PIid,
                'PNType': PermissionNotesType.pi.value,
                'PINaction': '创建权限标签{}'.format(pi.PIname),
            }
            db.session.add(pi)
            db.session.add(PermissionNotes.create(ptn_pi))
        pe = Permission.query.filter_by_(PTid=pt.PTid, PELevel=data.get('pelevel'), PIid=pi.PIid).first()
        pelevel = data.get('pelevel')
        if not pelevel:
            pelevel_model = Permission.query.filter_by_(PTid=data.get('ptid')).order_by(Permission.PELevel.desc()).first()
            pelevel = pelevel_model.PElevel + 1

        if not pe:
            pe = Permission.create({
                'PEid': str(uuid.uuid1()),
                'PELevel': int(pelevel),
                'PIid': pi.PIid,
                'PTid': pt.PTid
            })
            db.session.add(pe)

            ptn_pe = {
                'PNid': str(uuid.uuid1()),
                'ADid': admin.ADid,
                'PNcontent': pe.PEid,
                'PNType': PermissionNotesType.pe.value,
                'PINaction': '创建 {2} 权限 {0} 等级 {1}'.format(
                pt.PTname, pelevel, pi.PIname),
            }
            db.session.add(PermissionNotes.create(ptn_pe))

        adp_instance_list = []
        for ad in ad_list:
            adp_check = AdminPermission.query.filter_by_(ADid=ad, PIid=pi.PIid).first()
            if adp_check:
                continue
            adp = AdminPermission.create({
                'ADPid': str(uuid.uuid1()),
                'ADid': ad,
                'PIid': pi.PIid
            })
            adp_instance_list.append(adp)
        db.session.add_all(adp_instance_list)
        return Success('创建审批类型成功')

    @token_required
    def list_approval_notes(self):
        """查看审批流水"""
        data = parameter_required()
        approval = Approval.query.filter(
            Approval.isdelete == False,
            Approval.PTid == data.get('ptid'),
            Approval.AVcontent == data.get('avcontent')
        ).order_by(Approval.createtime.desc()).first_('不存在审批')
        approval_notes = ApprovalNotes.query.filter(
            ApprovalNotes.isdelete == False,
            ApprovalNotes.AVid == approval.AVid
        ).order_by(ApprovalNotes.createtime.desc()).all()
        approval.fill('notes', approval_notes)
        for approval_note in approval_notes:
            approval_note.add('createtime')
            approval_note.fill('ANaction_zh', ApprovalAction(approval_note.ANaction).zh_value)
        return Success(data=approval)

    @get_session
    @token_required
    def delete_permission(self):
        if not is_hign_level_admin():
            raise AuthorityError('非超级管理员')
        admin = Admin.query.filter_by_(ADid=request.user.id).first_('权限已失效')
        if admin.ADlevel != AdminLevel.super_admin.value:
            raise AuthorityError('权限已被回收')

        data = parameter_required(('actiontype', 'actionid'))
        # aptype = PermissionNotesType(data.get('aptype')).value
        # if aptype == PermissionNotesType.pi.value:
        # actiontype = PermissionNotesType(data.get('actiontype')).value
        actiontype = getattr(PermissionNotesType, data.get('actiontype'))
        if not actiontype:
            raise ParamsError('操作异常 actiontype')
        actiontype = actiontype.value
        actionid = data.get('actionid')

        ptn = {
            'PNid': str(uuid.uuid1()),
            'ADid': admin.ADid,
            'PNcontent': actionid,
            'PNType': actiontype,
        }
        if actiontype == PermissionNotesType.pi.value:
            pi = PermissionItems.query.filter_by_(PIid=actionid).first()
            self.__check_pelevel_by_pi(pi)
            pi.isdelete = True
            ptn.setdefault('PINaction', '{0}删除权限标签 {1}'.format(admin.ADname, pi.PIname))
        elif actiontype == PermissionNotesType.pe.value:
            pe = Permission.query.filter_by_(PEid=actionid).first()
            self.__check_pelevel_by_pe(pe)
            pe.isdelete = True
            ptn.setdefault('PINaction', '{0} 删除权限 {1}'.format(admin.ADname, pe.PEid))
        elif actiontype == PermissionNotesType.pt.value():
            pt = PermissionType.query.filter_by_(PTid=actionid).first()
            if pt:
                pt.isdelete = True
                ptn.setdefault('PINaction', '{0}删除权限类型 {1}'.format(admin.ADname, pt.PTname),)
        elif actiontype == PermissionNotesType.adp.value:
            adp = AdminPermission.qeury.filter_by_(ADPid=actionid).first()
            if adp:
                adp.isdelete = True
                ptn.setdefault('PINaction', '{0} 删除{2}权限标签下管理员 {1}'.format(admin.ADname, adp.ADid, adp.PIid))
        else:
            raise ParamsError('操作异常')

        return Success('删除成功')

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
        elif approval_model.PTid == 'toactivationcode':
            self.agree_activationcode(approval_model)
        elif approval_model.PTid == 'tosettlenment':
            self.agree_settlenment(approval_model)
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
        elif approval_model.PTid == 'toactivationcode':
            self.refuse_activationcode(approval_model, refuse_abo)
        elif approval_model.PTid == 'toreturn':
            # todo 退货申请目前没有图
            # return ParamsError('退货申请前往订单页面实现')
            pass
        elif approval_model.PTid == 'tosettlenment':
            self.refuse_settlenment(approval_model, refuse_abo)
        else:
            return ParamsError('参数异常，请检查审批类型是否被删除。如果新增了审批类型，请联系开发实现后续逻辑')

    def __check_pelevel_by_pi(self, pi):
        if not pi:
            return
        pe_list = Permission.query.filter_by_(PIid=pi.PIid).all()
        if not pe_list:
            return
        for pe in pe_list:
            self.__check_pelevel_by_pe(pe)
            pe.isdelete = True

    def __check_pelevel_by_pe(self, pe):
        if not pe:
            return
        pelevel = pe.PELevel
        pe_check_list = Permission.query.filter(
            Permission.PELevel == pelevel,
            Permission.PTid == pe.PTid,
            Permission.PEid != pe.PEid,
            Permission.isdelete == False
        ).all()
        if pe_check_list:
            return
        pe_max_level_model = Permission.query.filter_by_(PTid=pe.PTid).order_by(Permission.PELevel.desc()).first()

        if pe_max_level_model.PELevel == pelevel:
            return
        max_level = pe_max_level_model.PELevel
        for level in range(pelevel + 1, max_level + 1):
            pe_fix_list = Permission.query.filter_by_(PTid=pe.PTid, PELevel=level).all()
            for pe_fix in pe_fix_list:
                pe_fix.PELevel = level - 1

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
        uw = UserWallet.query.filter_by_(USid=cn.USid).first_("提现审批异常数据")
        # 拒绝提现时，回退申请的钱到可提现余额里
        uw.UWcash = float('%.2f' %(float(uw.UWcash) + float(cn.CNcashNum)))

    def agree_agent(self, approval_model):
        user = User.query.filter_by_(USid=approval_model.AVstartid).first_('数据异常')
        user.USlevel = UserIdentityStatus.agent.value
        uw = UserWallet.query.filter_by_(USid=user.USid).first()
        if not uw:
            db.session.add(UserWallet.create({
                'UWid': str(uuid.uuid1()),
                'USid': user.USid,
                'UWbalance': 0,
                'UWtotal': 0,
                'UWcash': 0,
                'UWexpect': 0
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
        product = Products.query.filter_by_(
            PRid=approval_model.AVcontent,
            PRstatus=ProductStatus.auditing.value
        ).first_('商品已处理')
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
        news.NErefusereason = refuse_abo

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
        # 是否进行库存变化
        other_apply_info = GuessNumAwardApply.query.filter(GuessNumAwardApply.isdelete == False,
                                                           GuessNumAwardApply.GNAAid != gnaa.GNAAid,
                                                           GuessNumAwardApply.GNAAstatus.notin_(
                                                               [ApplyStatus.cancle.value,
                                                                ApplyStatus.reject.value]),
                                                           GuessNumAwardApply.OSid == gnaa.OSid,
                                                           ).first()
        if not other_apply_info:
            out_stock = OutStock.query.filter(OutStock.isdelete == False, OutStock.OSid == gnaa.OSid
                                              ).first()
            from planet.control.COrder import COrder
            COrder()._update_stock(out_stock.OSnum, skuid=gnaa.SKUid)

    def agree_magicbox(self, approval_model):
        mba = MagicBoxApply.query.filter_by_(MBAid=approval_model.AVcontent).first_('魔盒商品申请数据异常')
        mba.MBAstatus = ApplyStatus.agree.value
        mba_other = MagicBoxApply.query.filter(
            MagicBoxApply.isdelete == False,
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
        # 是否进行库存变化
        other_apply_info = MagicBoxApply.query.filter(MagicBoxApply.isdelete == False,
                                                      MagicBoxApply.MBAid != mba.MBAid,
                                                      MagicBoxApply.MBAstatus.notin_(
                                                          [ApplyStatus.cancle.value, ApplyStatus.reject.value]),
                                                      MagicBoxApply.OSid == mba.OSid,
                                                      ).first()
        if not other_apply_info:
            out_stock = OutStock.query.filter(OutStock.isdelete == False,
                                              OutStock.OSid == mba.OSid
                                              ).first()
            from planet.control.COrder import COrder
            COrder()._update_stock(out_stock.OSnum, skuid=mba.SKUid)

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
        tc.AgreeStartTime = tc.ApplyStartTime
        tc.AgreeEndTime = tc.ApplyEndTime  # todo 同意时自动填写申请时间，后期可能需要管理同意时输入灵活时间

    def refuse_trialcommodity(self, approval_model, refuse_abo):
        tc = TrialCommodity.query.filter_by_(TCid=approval_model.AVcontent).first_('试用商品申请数据异常')
        tc.TCstatus = TrialCommodityStatus.reject.value
        tc.TCrejectReason = refuse_abo

    def agree_activationcode(self, approval_model):
        aca = ActivationCodeApply.query.filter_by_(ACAid=approval_model.AVcontent).first_('激活码申请数据异常')
        aca.ACAapplyStatus = ApplyStatus.agree.value
        from planet.control.CActivationCode import CActivationCode
        caca = CActivationCode()
        code_list = caca._generate_activaty_code()
        uac_list = []
        for code in code_list:
            uac = UserActivationCode.create({
                'UACid': str(uuid.uuid1()),
                'USid': aca.USid,
                'UACcode': code,
                'UACstatus': 0,
            })
            uac_list.append(uac)
        db.session.add_all(uac_list)

    def refuse_activationcode(self, approval_model, refuse_abo):
        aca = ActivationCodeApply.query.filter_by_(ACAid=approval_model.AVcontent).first_('激活码申请数据异常')
        aca.ACAapplyStatus = ApplyStatus.reject.value

    def get_avstatus(self):
        data = {level.name: level.zh_value for level in ApplyStatus}
        return Success('获取所有状态成功', data=data)

    def agree_settlenment(self, approval_model):
        ssa = SettlenmentApply.query.filter(
            SettlenmentApply.SSAid == approval_model.AVcontent,
            SettlenmentApply.isdelete == False).first_('结算申请数据异常')
        ssa.SSAstatus = ApplyStatus.agree.value

        ss = SupplizerSettlement.query.filter(
            SupplizerSettlement.SSid == ssa.SSid, SupplizerSettlement.isdelete == False).first_('结算申请数据异常')
        ss.SSstatus = SupplizerSettementStatus.settlementing.value

    def refuse_settlenment(self, approval_model, refuse_abo):
        ssa = SettlenmentApply.query.filter(
            SettlenmentApply.SSAid == approval_model.AVcontent,
            SettlenmentApply.isdelete == False).first_('结算申请数据异常')
        ssa.SSAstatus = ApplyStatus.reject.value

        ss = SupplizerSettlement.query.filter(
            SupplizerSettlement.SSid == ssa.SSid, SupplizerSettlement.isdelete == False).first_('结算申请数据异常')

        ss.SSstatus = SupplizerSettementStatus.settlementing.value
