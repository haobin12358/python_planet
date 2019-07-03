# -*- coding: utf-8 -*-
import uuid
import re
from datetime import datetime
from flask import current_app, request
from sqlalchemy import or_, false

from planet.common.error_response import ParamsError
from planet.common.params_validates import parameter_required
from planet.common.success_response import Success
from planet.common.token_handler import admin_required, is_admin
from planet.config.enums import AdminActionS
from planet.extensions.register_ext import db
from planet.models.user import AddressArea, AddressCity, AddressProvince, Admin
from planet.models.scenicspot import ScenicSpot
from planet.control.BaseControl import BASEADMIN


class CScenicSpot(object):

    def __init__(self):
        self.BaseAdmin = BASEADMIN()

    @admin_required
    def add(self):
        """添加景区介绍"""
        admin = Admin.query.filter_by_(ADid=getattr(request, 'user').id).first_('请重新登录')
        data = parameter_required(('aaid', 'sspcontent', 'sspname', 'ssplevel', 'sspmainimg'))
        aaid, sspcontent, ssplevel = data.get('aaid'), data.get('sspcontent'), data.get('ssplevel')
        sspname = data.get('sspname')
        parentid = data.get('parentid')
        exsit = ScenicSpot.query.filter(ScenicSpot.isdelete == false(), ScenicSpot.SSPname == sspname).first()
        if exsit:
            raise ParamsError('已添加过该景区')
        if parentid:
            ScenicSpot.query.filter(ScenicSpot.SSPid == parentid, ScenicSpot.isdelete == false(),
                                    ScenicSpot.ParentID.is_(None)).first_('关联景区选择错误')
        # 地址拼接
        address = db.session.query(AddressProvince.APname, AddressCity.ACname, AddressArea.AAname).filter(
            AddressArea.ACid == AddressCity.ACid, AddressCity.APid == AddressProvince.APid,
            AddressArea.AAid == aaid).first_('地址有误')
        address = '-'.join(address)
        if not re.match(r'^[1-5]$', str(ssplevel)):
            raise ParamsError('景区等级请填写1到5之间的整数')
        with db.auto_commit():
            scenic_instance = ScenicSpot.create({
                'SSPid': str(uuid.uuid1()),
                'ADid': admin.ADid,
                'AAid': aaid,
                'SSParea': address,
                'SSPcontent': sspcontent,
                'SSPname': sspname,
                'SSPlevel': ssplevel,
                'SSPmainimg': data.get('sspmainimg'),
                'ParentID': parentid
            })
            db.session.add(scenic_instance)
            self.BaseAdmin.create_action(AdminActionS.insert.value, 'ScenicSpot', scenic_instance.SSPid)
        return Success('添加成功', {'sspid': scenic_instance.SSPid})

    @admin_required
    def update(self):
        """更新景区介绍"""
        admin = Admin.query.filter_by_(ADid=getattr(request, 'user').id).first_('请重新登录')
        data = parameter_required(('sspid', 'aaid', 'sspcontent', 'sspname', 'ssplevel', 'sspmainimg'))
        aaid, sspcontent, ssplevel = data.get('aaid'), data.get('sspcontent'), data.get('ssplevel')
        sspid = data.get('sspid')
        scenic_instance = ScenicSpot.query.filter_by_(SSPid=sspid).first_('未找到该景区信息')
        sspname = data.get('sspname')
        parentid = data.get('parentid')

        if parentid == sspid:
            raise ParamsError('关联景区不能选择自身')
        associated = ScenicSpot.query.filter_by_(ParentID=scenic_instance.SSPid).first()
        if not scenic_instance.ParentID and associated and parentid:
            raise ParamsError('该景区作为顶级景区已被其他景区关联，不允许再将此景区关联到其他景区下')

        exsit_other = ScenicSpot.query.filter(ScenicSpot.isdelete == false(),
                                              ScenicSpot.SSPname == sspname,
                                              ScenicSpot.SSPid != sspid).first()
        if exsit_other:
            raise ParamsError('景区名称重复')
        if parentid:
            ScenicSpot.query.filter(ScenicSpot.SSPid == parentid, ScenicSpot.isdelete == false(),
                                    ScenicSpot.ParentID.is_(None)).first_('关联景区选择错误')

        # 地址拼接
        address = db.session.query(AddressProvince.APname, AddressCity.ACname, AddressArea.AAname).filter(
            AddressArea.ACid == AddressCity.ACid, AddressCity.APid == AddressProvince.APid,
            AddressArea.AAid == aaid).first_('地址有误')
        address = '-'.join(address)
        if not re.match(r'^[1-5]$', str(ssplevel)):
            raise ParamsError('景区等级请填写1到5之间的整数')
        with db.auto_commit():
            scenic_instance.update({
                'AAid': aaid,
                'ADid': admin.ADid,
                'SSParea': address,
                'SSPcontent': sspcontent,
                'SSPname': sspname,
                'SSPlevel': ssplevel,
                'SSPmainimg': data.get('sspmainimg'),
                'ParentID': parentid
            }, null='no')
            db.session.add(scenic_instance)
            self.BaseAdmin.create_action(AdminActionS.update.value, 'ScenicSpot', scenic_instance.SSPid)
        return Success('更新成功', {'sspid': scenic_instance.SSPid})

    @admin_required
    def delete(self):
        """删除景区"""
        sspid = parameter_required(('sspid', )).get('sspid')
        scenic_instance = ScenicSpot.query.filter_by_(SSPid=sspid).first_('未找到该景区信息')
        with db.auto_commit():
            scenic_instance.update({'isdelete': True})
            db.session.add(scenic_instance)
            self.BaseAdmin.create_action(AdminActionS.delete.value, 'ScenicSpot', scenic_instance.SSPid)
        return Success('删除成功', {'sspid': sspid})

    @staticmethod
    def _get_root_scenicspots():
        root_scenicspots = db.session.query(ScenicSpot.SSPid, ScenicSpot.SSPname
                                            ).filter(ScenicSpot.isdelete == false(),
                                                     ScenicSpot.ParentID.is_(None)).all()
        res = []
        for rscenicspot in root_scenicspots:
            res.append({'sspid': rscenicspot[0],
                        'sspname': rscenicspot[1]
                        })
        return Success(data=res)

    def list(self):
        """景区列表"""
        args = parameter_required(('page_num', 'page_size'))
        option = args.get('option')
        if option and str(option) == 'root':  # 只获取可被关联的一级景区
            return self._get_root_scenicspots()

        order_dict = {'level': ScenicSpot.SSPlevel}
        try:
            order = args.get('order', 'level|desc')
            order_type, order_queue = order.split('|')
            assert order_queue in ['desc', 'asc']
        except Exception as e:
            current_app.logger.error('顺序参数错误: {}'.format(e))
            order_type, order_queue = 'level', 'desc'
        current_app.logger.info('get order_type: {} / order_queue: {}'.format(order_type, order_queue))
        if order_queue == 'desc':
            ssp_order = order_dict.get(order_type).desc()
        else:
            ssp_order = order_dict.get(order_type).asc()

        filter_args = []
        sspname, ssparea = args.get('sspname'), args.get('ssparea')
        if sspname:
            filter_args.append(or_(*[ScenicSpot.SSPname.ilike('%{}%'.format(x)) for x in str(sspname).split()]))
        if ssparea:
            filter_args.append(or_(*[ScenicSpot.SSParea.ilike('%{}%'.format(x)) for x in str(ssparea).split()]))
        current_app.logger.info('start query : {}'.format(datetime.now()))
        all_scenicspot = ScenicSpot.query.filter(ScenicSpot.isdelete == false(),
                                                 *filter_args).order_by(ssp_order,
                                                                        ScenicSpot.createtime.desc()
                                                                        ).all_with_page()
        current_app.logger.info('query finished : {}'.format(datetime.now()))
        for scenicspot in all_scenicspot:
            parent = None
            if scenicspot.ParentID and is_admin():
                parent_scenicspot = db.session.query(ScenicSpot.SSPid, ScenicSpot.SSPname
                                                     ).filter_by_(SSPid=scenicspot.ParentID).first()
                if parent_scenicspot:
                    parent = {'sspid': parent_scenicspot[0], 'sspname': parent_scenicspot[1]}
            scenicspot.fill('parent_scenicspot', parent)
            scenicspot.fill('associated', bool(parent))
            scenicspot.hide('ParentID', 'ADid', 'SSPcontent')
        current_app.logger.info('fill finished : {}'.format(datetime.now()))

        return Success(data=all_scenicspot)

    def get(self):
        """景区详情"""
        args = parameter_required(('sspid', ))
        sspid = args.get('sspid')
        scenicspot = ScenicSpot.query.filter_by_(SSPid=sspid).first_('未找到该景区信息')
        scenicspot.hide('ParentID', 'ADid')
        parent = address_info = None
        if is_admin():
            # 地址处理
            address = db.session.query(AddressProvince.APid, AddressProvince.APname, AddressCity.ACid,
                                       AddressCity.ACname, AddressArea.AAid, AddressArea.AAname).filter(
                AddressArea.ACid == AddressCity.ACid, AddressCity.APid == AddressProvince.APid,
                AddressArea.AAid == scenicspot.AAid).first_('地址有误')
            address_info = [{'apid': address[0], 'apname': address[1]},
                            {'acid': address[2], 'acname': address[3]},
                            {'aaid': address[4], 'aaname': address[5]}]
            # 关联景区
            if scenicspot.ParentID:
                parent_scenicspot = db.session.query(ScenicSpot.SSPid, ScenicSpot.SSPname
                                                     ).filter_by_(SSPid=scenicspot.ParentID).first()
                if parent_scenicspot:
                    parent = {'sspid': parent_scenicspot[0], 'sspname': parent_scenicspot[1]}
        scenicspot.fill('parent_scenicspot', parent)
        scenicspot.fill('associated', bool(parent))
        scenicspot.fill('address_info', address_info)
        return Success(data=scenicspot)



