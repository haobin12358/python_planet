# -*- coding: utf-8 -*-
import json
import uuid
import re
from datetime import datetime
from flask import current_app, request
from sqlalchemy import or_, false, extract, and_, func
from planet.common.error_response import ParamsError, TokenError
from planet.common.params_validates import parameter_required, validate_price
from planet.common.success_response import Success
from planet.common.token_handler import admin_required, is_admin, phone_required, common_user
from planet.config.enums import AdminActionS, TravelRecordType, TravelRecordStatus, MiniUserGrade, CollectionType, \
    EnterLogStatus, ApplyFrom, ApprovalAction, ApplyStatus
from planet.config.http_config import API_HOST
from planet.extensions.register_ext import db, mp_miniprogram
from planet.extensions.weixin.mp import WeixinMPError
from planet.models import EnterLog, Play, Approval
from planet.models.user import AddressArea, AddressCity, AddressProvince, Admin, User, UserCollectionLog
from planet.models.scenicspot import ScenicSpot, TravelRecord, Toilet, CustomizeShareContent
from planet.control.BaseControl import BASEADMIN, BaseController, BASEAPPROVAL
from planet.control.CPlay import CPlay
from planet.control.CUser import CUser
from pyquery import PyQuery


class CScenicSpot(BASEAPPROVAL):

    def __init__(self):
        self.BaseAdmin = BASEADMIN()
        self.BaseController = BaseController()
        self.cplay = CPlay()
        self.cuser = CUser()
        # self.scale_dict = {3: 1000000, 4: 500000, 5: 200000, 6: 100000, 7: 50000,
        #                    8: 50000, 9: 20000, 10: 10000, 11: 5000, 12: 2000, 13: 1000,
        #                    14: 500, 15: 200, 16: 100, 17: 50, 18: 50, 19: 20, 20: 10}
        self.scale_dict = {3: 10, 4: 10, 5: 10, 6: 10, 7: 5,
                           8: 4, 9: 3, 10: 3, 11: 2, 12: 2, 13: 1,
                           14: 1, 15: 1, 16: 1, 17: 1, 18: 1, 19: 1, 20: 1}

    @staticmethod
    def ac_callback():
        return mp_miniprogram.access_token

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
        sspid = parameter_required(('sspid',)).get('sspid')
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

    @staticmethod
    def _get_search_scenicspots(args):
        sspname = args.get('sspname')
        all_scenicspot = db.session.query(ScenicSpot.SSPid, ScenicSpot.SSPname).filter(
            ScenicSpot.isdelete == false(),
            or_(*map(lambda i: ScenicSpot.SSPname.ilike('%{}%'.format(i)),
                     map(lambda x: re.escape(x) if '_' not in x else re.sub(r'_', r'\_', x), str(sspname).split())))
        ).all()
        res = []
        for rscenicspot in all_scenicspot:
            res.append({'sspid': rscenicspot[0],
                        'sspname': rscenicspot[1]
                        })
        return Success(data=res)

    def list(self):
        """景区列表"""
        args = parameter_required(('page_num', 'page_size'))
        option = args.get('option')
        if option:
            if str(option) == 'root':  # 只获取可被关联的一级景区
                return self._get_root_scenicspots()
            if str(option) == 'search':  # 仅用于模糊搜索
                return self._get_search_scenicspots(args)
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
        sspname, ssparea, ssplevel = args.get('sspname'), args.get('ssparea'), args.get('ssplevel')
        if sspname:
            filter_args.append(or_(*map(lambda i: ScenicSpot.SSPname.ilike('%{}%'.format(i)),
                                        map(lambda x: re.escape(x) if '_' not in x else re.sub(r'_', r'\_', x),
                                            str(sspname).split()))))
        if ssparea:
            filter_args.append(or_(*map(lambda i: ScenicSpot.SSParea.ilike('%{}%'.format(i)),
                                        map(lambda x: re.escape(x) if '_' not in x else re.sub(r'_', r'\_', x),
                                            str(ssparea).split()))))
        if ssplevel:
            if not re.match(r'^[12345]$', str(ssplevel)):
                raise ParamsError('ssplevel 参数错误')
            filter_args.append(ScenicSpot.SSPlevel == ssplevel)

        current_app.logger.info('start query : {}'.format(datetime.now()))
        all_scenicspot = ScenicSpot.query.filter(ScenicSpot.isdelete == false(), *filter_args
                                                 ).order_by(ssp_order, ScenicSpot.createtime.desc()).all_with_page()
        current_app.logger.info('query finished : {}'.format(datetime.now()))
        for scenicspot in all_scenicspot:
            parent = None
            if scenicspot.ParentID:
                parent_scenicspot = db.session.query(ScenicSpot.SSPid, ScenicSpot.SSPname
                                                     ).filter_by_(SSPid=scenicspot.ParentID).first()
                if parent_scenicspot:
                    parent = {'sspid': parent_scenicspot[0], 'sspname': parent_scenicspot[1]}
            scenicspot.fill('parent_scenicspot', parent)
            scenicspot.fill('associated', bool(parent))
            scenicspot.hide('ParentID', 'ADid', 'SSPcontent')
            scenicspot.fill('raiders_num', db.session.query(TravelRecord.TRid).filter(
                TravelRecord.isdelete == false(),
                TravelRecord.TRtype == TravelRecordType.raiders.value,
                TravelRecord.TRlocation.ilike('%{}%'.format(scenicspot.SSPname))).count())
        current_app.logger.info('fill finished : {}'.format(datetime.now()))

        return Success(data=all_scenicspot)

    def get(self):
        """景区详情"""
        args = parameter_required(('sspid',))
        sspid = args.get('sspid')
        scenicspot = ScenicSpot.query.filter_by_(SSPid=sspid).first_('未找到该景区信息')
        scenicspot.hide('ParentID', 'ADid')
        parent = address_info = None
        recommend_raiders = []
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
        if not is_admin():  # 非管理员显示推荐攻略
            recommend_raiders = TravelRecord.query.filter(
                TravelRecord.isdelete == false(),
                TravelRecord.TRtype == TravelRecordType.raiders.value,
                TravelRecord.TRlocation.ilike('%{}%'.format(scenicspot.SSPname))
            ).order_by(TravelRecord.createtime.desc()).limit(2).all()
            [self._fill_raiders_list(x) for x in recommend_raiders]
        scenicspot.fill('parent_scenicspot', parent)
        scenicspot.fill('associated', bool(parent))
        scenicspot.fill('address_info', address_info)
        scenicspot.fill('recommend_raiders', recommend_raiders)
        return Success(data=scenicspot)

    def get_raiders_list(self):
        """获取景区下推荐攻略列表"""
        args = parameter_required(('sspid',))
        sspid = args.get('sspid')
        scenicspot = ScenicSpot.query.filter_by_(SSPid=sspid).first_('未找到该景区信息')
        raiders = TravelRecord.query.filter(TravelRecord.isdelete == false(),
                                            TravelRecord.TRtype == TravelRecordType.raiders.value,
                                            TravelRecord.TRlocation.ilike('%{}%'.format(scenicspot.SSPname))
                                            ).order_by(TravelRecord.createtime.desc()).all_with_page()
        [self._fill_raiders_list(x) for x in raiders]
        return Success(data=raiders)

    @phone_required
    def del_travelrecord(self):
        """删除时光记录"""
        User.query.filter_by_(USid=getattr(request, 'user').id).first_('请重新登录')
        trid = parameter_required('trid').get('trid')
        travelrecord = TravelRecord.query.filter(TravelRecord.isdelete == false(),
                                                 TravelRecord.TRid == trid).first_('未找到该记录')
        with db.auto_commit():
            travelrecord.update({'isdelete': True})
            db.session.add(travelrecord)
        return Success('删除成功', {'trid': trid})

    @phone_required
    def add_travelrecord(self):
        """创建时光记录"""
        user = User.query.filter_by_(USid=getattr(request, 'user').id).first_('请重新登录')
        data = parameter_required(('trtype', 'trstatus'))
        plid = data.get('plid')
        try:
            TravelRecordStatus(data.get('trstatus'))
        except Exception:
            raise ParamsError('trstatus 参数错误')
        trtype = str(data.get('trtype'))
        if trtype == str(TravelRecordType.raiders.value):  # 攻略
            parameter_required({'trproducts': '推荐携带物品', 'trbudget': '预算',
                                'trcontent': '活动详情', 'trlocation': '景区'}, datafrom=data)
            tr_dict = self._create_raiders(data)
        elif trtype == str(TravelRecordType.travels.value):  # 游记
            parameter_required({'trtitle': '标题', 'trcontent': '游记内容', 'trlocation': '景区'}, datafrom=data)
            tr_dict = self._create_travels(data)
        elif trtype == str(TravelRecordType.essay.value):  # 随笔
            parameter_required({'text': '随笔内容'}, datafrom=data)
            tr_dict = self._create_essay(data)
        else:
            raise ParamsError('type 参数错误')
        with db.auto_commit():
            travelrecord_dict = {'TRid': str(uuid.uuid1()),
                                 'AuthorID': user.USid,
                                 'TRtype': trtype,
                                 'TRstatus': data.get('trstatus'),
                                 # 'TRstatus': TravelRecordStatus.auditing.value  # todo 待审核状态
                                 'PLid': plid if plid else None
                                 }
            travelrecord_dict.update(tr_dict)
            try:
                check_content = travelrecord_dict.get('TRcontent')
                if trtype == str(TravelRecordType.essay.value):
                    check_content = json.loads(check_content).get('text')
                mp_miniprogram.msg_sec_check(check_content)
            except WeixinMPError:
                travelrecord_dict['isdelete'] = True
            db.session.add(TravelRecord.create(travelrecord_dict))
        try:
            current_app.logger.info('content_sec_check: {}'.format(mp_miniprogram.msg_sec_check(check_content)))
        except WeixinMPError:
            raise ParamsError('您输入的内容含有部分敏感词汇,请检查后重新发布')
        return Success('发布成功', {'trid': travelrecord_dict['TRid']})

    @staticmethod
    def _create_raiders(data):
        """攻略"""
        trproducts, trbudget = data.get('trproducts'), data.get('trbudget')
        trbudget = validate_price(trbudget)
        if not isinstance(trproducts, list):
            raise ParamsError('trproducts 格式错误')
        trproducts = json.dumps(trproducts)
        return {'TRproducts': trproducts,
                'TRbudget': trbudget,
                'TRcontent': data.get('trcontent'),
                'TRlocation': data.get('trlocation')
                }

    @staticmethod
    def _create_travels(data):
        """游记"""
        return {'TRtitle': data.get('trtitle'),
                'TRcontent': data.get('trcontent'),
                'TRlocation': data.get('trlocation')
                }

    def _create_essay(self, data):
        """随笔"""
        text, image, video = data.get('text'), data.get('image'), data.get('video')
        # if image:
        #     current_app.logger.error("图片校验测试")
        #     current_app.logger.error(mp_miniprogram.img_sec_check(image))
        if image and not isinstance(image, list):
            raise ParamsError('image 格式错误')
        if image and video:
            raise ParamsError('不能同时选择图片和视频')
        if image and len(image) > 9:
            raise ParamsError('最多可上传9张图片')
        video = {'url': self._check_upload_url(video.get('url')),
                 'thumbnail': video.get('thumbnail'),
                 'duration': video.get('duration')
                 } if video else None
        content = {'text': text,
                   'image': [self._check_upload_url(i, msg='图片格式错误, 请检查后重新上传') for i in image] if image else None,
                   'video': video
                   }
        content = json.dumps(content)
        return {'TRcontent': content,
                'TRlocation': data.get('trlocation')
                }

    @staticmethod
    def _check_upload_url(url, msg='视频上传出错，请重新上传(视频时长需大于3秒，小于60秒)'):
        if not url or str(url).endswith('undefined'):
            raise ParamsError(msg)
        return url

    def travelrecord_list(self):
        """时光记录（个人中心）列表"""
        args = request.args.to_dict()
        usid, date, area, trtype = args.get('usid'), args.get('date'), args.get('area'), args.get('trtype')
        option = args.get('option')
        if usid:
            ucl_list = [usid]
            counts = self._my_home_page_count(usid)
            top = self._init_top_dict(counts)
        elif common_user():
            ucl_list = db.session.query(UserCollectionLog.UCLcollection).filter(
                UserCollectionLog.UCLcoType == CollectionType.user.value,
                UserCollectionLog.isdelete == false(),
                UserCollectionLog.UCLcollector == getattr(request, 'user').id).all()
            ucl_list = [ucl[0] for ucl in ucl_list]
            counts = self._my_home_page_count(getattr(request, 'user').id)
            top = self._init_top_dict(counts)
        elif is_admin():
            ucl_list = top = None
        else:
            # return Success(data={'top': {'followed': 0, 'fens': 0, 'published': 0,
            #                              'usname': None, 'usheader': None, 'usminilevel': None, 'concerned': False},
            #                      'travelrecord': []})
            raise TokenError('请重新登录')
        base_filter = [TravelRecord.isdelete == false()]
        if not (common_user() and option == 'my') and not is_admin():
            base_filter.append(TravelRecord.AuthorID.in_(ucl_list))
            base_filter.append(TravelRecord.TRstatus == TravelRecordStatus.published.value)
        trecords_query = TravelRecord.query.filter(*base_filter)
        if date:
            if not re.match(r'^\d{4}-\d{2}$', date):
                raise ParamsError('查询日期格式错误')
            year, month = str(date).split('-')
            trecords_query = trecords_query.filter(extract('month', TravelRecord.createtime) == month,
                                                   extract('year', TravelRecord.createtime) == year)
        if trtype or str(trtype) == '0':
            if not re.match(r'^[012]$', str(trtype)):
                raise ParamsError('trtype 参数错误')
            trecords_query = trecords_query.filter(TravelRecord.TRtype == trtype)
        if area:
            scenicspots = db.session.query(ScenicSpot.SSPname).filter(ScenicSpot.isdelete == false(),
                                                                      ScenicSpot.SSParea.ilike('%{}%'.format(area))
                                                                      ).all()
            ssname = [ss[0] for ss in scenicspots]
            trecords_query = trecords_query.filter(
                or_(*map(lambda x: TravelRecord.TRlocation.ilike('%{}%'.format(x)), ssname)))
        if common_user() and option == 'my':
            trecords_query = trecords_query.filter(TravelRecord.AuthorID == getattr(request, 'user').id)
        trecords = trecords_query.order_by(TravelRecord.createtime.desc()).all_with_page()
        [self._fill_travelrecord(x) for x in trecords]
        return Success(data={'top': top, 'travelrecord': trecords})

    @staticmethod
    def _init_top_dict(counts):
        return {'followed': counts[0], 'fens': counts[1], 'published': counts[2],
                'usname': counts[3], 'usheader': counts[4], 'usminilevel': counts[5], 'concerned': counts[6]}

    @staticmethod
    def _my_home_page_count(usid):
        followed = UserCollectionLog.query.filter(UserCollectionLog.isdelete == false(),
                                                  UserCollectionLog.UCLcollector == usid,
                                                  UserCollectionLog.UCLcoType == CollectionType.user.value,
                                                  ).count()
        fens = UserCollectionLog.query.filter(UserCollectionLog.isdelete == false(),
                                              UserCollectionLog.UCLcollection == usid,
                                              UserCollectionLog.UCLcoType == CollectionType.user.value,
                                              ).count()
        published = TravelRecord.query.filter(TravelRecord.isdelete == false(),
                                              TravelRecord.AuthorID == usid).count()
        user = User.query.filter_by_(USid=usid).first()
        follow_status = True if common_user() and UserCollectionLog.query.filter(
            UserCollectionLog.isdelete == false(),
            UserCollectionLog.UCLcollector == getattr(request, 'user').id,
            UserCollectionLog.UCLcollection == usid,
            UserCollectionLog.UCLcoType == CollectionType.user.value).first() else False
        try:
            usminilevel = MiniUserGrade(user.USminiLevel).zh_value
        except Exception:
            usminilevel = None
        return (followed, fens, published, getattr(user, 'USname', None),
                getattr(user, 'USheader', None), usminilevel, follow_status)

    def get_travelrecord(self):
        """时光记录详情"""
        args = parameter_required(('trid',))
        trecord = TravelRecord.query.filter_by_(TRid=args.get('trid')).first_('未找到相应信息')
        self._fill_travelrecord(trecord)
        return Success(data=trecord)

    @staticmethod
    def _fill_travelrecord(trecord):
        """填充时光记录详情"""
        if trecord.TRtype == TravelRecordType.essay.value:  # 随笔
            trecord.fields = ['TRid', 'TRlocation', 'TRtype', 'TRstatus']
            content = json.loads(trecord.TRcontent)
            trecord.fill('text', content.get('text', '...'))
            trecord.fill('image', content.get('image'))
            trecord.fill('video', content.get('video'))
            if content.get('image'):
                showtype = 'image'
            elif content.get('video'):
                showtype = 'video'
            else:
                showtype = 'text'
            trecord.fill('showtype', showtype)
        elif trecord.TRtype == TravelRecordType.travels.value:  # 游记
            trecord.fields = ['TRid', 'TRlocation', 'TRtitle', 'TRtype', 'TRcontent', 'TRstatus']
            img_path = PyQuery(trecord.TRcontent)('img').attr('src')
            trecord.fill('picture', (img_path if str(img_path).startswith('http') else
                                     API_HOST + img_path if img_path else None))
            text_content = PyQuery(trecord.TRcontent)('p').eq(0).text()
            text_content = '{}...'.format(text_content) if text_content else None
            trecord.fill('text', text_content)
        else:  # 攻略
            trecord.fields = ['TRid', 'TRlocation', 'TRbudget', 'TRproducts', 'TRtype', 'TRcontent', 'TRstatus']
            trecord.fill('trtitle', '{}游玩攻略'.format(trecord.TRlocation))
            trproducts_str = None
            if trecord.TRproducts:
                trecord.TRproducts = json.loads(trecord.TRproducts)
                trproducts_str = '、'.join(map(lambda x: str(x), trecord.TRproducts))
            trecord.fill('trproducts_str', trproducts_str)
            if trecord.TRbudget:
                trecord.fill('trbudget_str', '¥{}'.format(round(float(trecord.TRbudget), 2)))
            img_path = PyQuery(trecord.TRcontent)('img').attr('src')
            trecord.fill('picture', (img_path if str(img_path).startswith('http') else
                                     API_HOST + img_path if img_path else None))
            text_content = PyQuery(trecord.TRcontent)('p').eq(0).text()
            text_content = '{}...'.format(text_content) if text_content else None
            trecord.fill('text', text_content)

        trecord.fill('travelrecordtype_zh',
                     TravelRecordStatus.auditing.zh_value if trecord.TRstatus == TravelRecordStatus.auditing.value
                     else TravelRecordType(trecord.TRtype).zh_value)
        trecord.fill('trstatus_zh', TravelRecordStatus(trecord.TRstatus).zh_value)
        author = User.query.filter_by_(USid=trecord.AuthorID).first()
        author_info = None if not author else {'usname': author.USname,
                                               'usid': author.USid,
                                               'usheader': author.USheader,
                                               'usminilevel': MiniUserGrade(author.USminiLevel).zh_value}

        trecord.fill('author', author_info)
        is_own = True if common_user() and getattr(request, 'user').id == trecord.AuthorID else False
        trecord.fill('is_own', is_own)
        followed = True if common_user() and UserCollectionLog.query.filter(
            UserCollectionLog.UCLcoType == CollectionType.user.value,
            UserCollectionLog.isdelete == false(),
            UserCollectionLog.UCLcollector == getattr(request, 'user').id,
            UserCollectionLog.UCLcollection == trecord.AuthorID).first() else False
        trecord.fill('followed', followed)

    @staticmethod
    def _fill_raiders_list(raiders):
        """攻略列表"""
        raiders.fields = ['TRid']
        raiders.fill('trtitle', '{}游玩攻略'.format(raiders.TRlocation))
        author = User.query.filter_by_(USid=raiders.AuthorID).first()
        author_info = None if not author else {'usname': author.USname,
                                               'usheader': author.USheader,
                                               'usid': author.USid,
                                               'usminilevel': MiniUserGrade(author.USminiLevel).zh_value}

        raiders.fill('author', author_info)
        raiders.fill('travelrecordtype_zh', TravelRecordType(raiders.TRtype).zh_value)
        img_path = PyQuery(raiders.TRcontent)('img').attr('src')
        raiders.fill('picture', img_path)
        followed = True if common_user() and UserCollectionLog.query.filter(
            UserCollectionLog.UCLcoType == CollectionType.user.value,
            UserCollectionLog.isdelete == false(),
            UserCollectionLog.UCLcollector == getattr(request, 'user').id,
            UserCollectionLog.UCLcollection == raiders.AuthorID).first() else False
        raiders.fill('followed', followed)
        is_own = True if common_user() and raiders.AuthorID == getattr(request, 'user').id else False
        raiders.fill('is_own', is_own)

    def get_team(self):
        """团队广场下内容"""
        data = parameter_required(('plid',))
        secret_usid = data.get('secret_usid')
        csc = None
        if secret_usid:
            csc = self.get_customize_share_content(secret_usid, data.get('plid'))
        if csc:
            current_app.logger.info('get cscid: {}'.format(csc.CSCid))
            trids = json.loads(csc.TRids)
            tr_list = TravelRecord.query.filter(TravelRecord.isdelete == false(), TravelRecord.TRid.in_(trids),
                                                TravelRecord.TRstatus == TravelRecordStatus.published.value
                                                )
            if trids:
                tr_list = tr_list.order_by(func.field(TravelRecord.TRid, *trids))
            tr_list = tr_list.all()
        else:
            tr_list = self._filter_team_travelrecord(data.get('plid')).all_with_page()
        [self._fill_travelrecord(x) for x in tr_list]
        return Success(data=tr_list)

    @staticmethod
    def _filter_team_travelrecord(plid):
        return TravelRecord.query.filter(
            Play.PLid == plid,
            Play.isdelete == false(),
            or_(and_(EnterLog.USid == TravelRecord.AuthorID,
                     Play.PLid == EnterLog.PLid,
                     EnterLog.isdelete == false(),
                     EnterLog.ELstatus == EnterLogStatus.success.value),
                Play.PLcreate == TravelRecord.AuthorID),
            or_(and_(TravelRecord.createtime <= Play.PLendTime,
                     TravelRecord.createtime >= Play.PLstartTime),
                TravelRecord.PLid == plid),
            TravelRecord.isdelete == false(),
            TravelRecord.AuthorType == ApplyFrom.user.value,
            TravelRecord.TRstatus == TravelRecordStatus.published.value).order_by(
            TravelRecord.createtime.desc())

    def get_team_album(self):
        """团队相册"""
        data = parameter_required('plid')
        secret_usid = data.get('secret_usid')
        csc = None
        if secret_usid:
            csc = self.get_customize_share_content(secret_usid, data.get('plid'), album=True)
        if csc:
            current_app.logger.info('get cscid: {}'.format(csc.CSCid))
            res = json.loads(csc.Album)
        else:
            res = []
            tr_list = self._filter_team_travelrecord(data.get('plid')).all()
            [res.extend(self._filter_media(tr)) for tr in tr_list]
        request.mount = len(res)
        return Success(data=res)

    def get_customize_share_content(self, secret_usid, plid, album=False):
        try:
            superid = self.cuser._base_decode(secret_usid)
            current_app.logger.info('secret_usid --> superid {}'.format(superid))
        except Exception as e:
            current_app.logger.error('解析secret_usid时失败： {}'.format(e))
            superid = ''
        csctype = 2 if request.url_root.endswith('share.bigxingxing.com:443/') or not album else 1
        csc = CustomizeShareContent.query.filter(CustomizeShareContent.isdelete == false(),
                                                 CustomizeShareContent.USid == superid,
                                                 CustomizeShareContent.CSCtype == csctype,
                                                 CustomizeShareContent.PLid == plid
                                                 ).order_by(CustomizeShareContent.createtime.desc()).first()
        return csc

    @staticmethod
    def _filter_media(trecord):
        res = []
        if trecord.TRtype == TravelRecordType.essay.value:  # 随笔
            content = json.loads(trecord.TRcontent)
            if content.get('image'):
                [res.append({'type': 'image', 'url': img if img.startswith('http') else API_HOST + img})
                 for img in content.get('image')]
            if content.get('video'):
                temp_dict = content.get('video')
                temp_dict['type'] = 'video'
                res.append(temp_dict)
        else:  # 游记、攻略
            images = PyQuery(trecord.TRcontent)('img')
            [res.append({'type': 'image', 'url': img.attrib.get('src') if str(img.attrib.get('src')).startswith(
                'http') else API_HOST + img.attrib.get('src') if img.attrib.get('src') else None}) for img in images]
        return res

    @phone_required
    def share_content(self):
        """分享前自定义内容"""
        data = parameter_required('plid')
        album, trids = data.get('album', []), data.get('trids', [])
        detail = data.get('detail')
        # if not album and not trids and detail:
        #     current_app.logger.info('本次未编辑内容')
        #     return Success()
        assert isinstance(album, list), 'album 格式错误'
        assert isinstance(trids, list), 'trids 格式错误'
        if not all(map(lambda x: isinstance(x, str), trids)):
            raise ParamsError('trids格式错误')
        with db.auto_commit():
            db.session.add(CustomizeShareContent.create({'CSCid': str(uuid.uuid1()),
                                                         'USid': getattr(request, 'user').id,
                                                         'PLid': data.get('plid'),
                                                         'Album': json.dumps(album),
                                                         'TRids': json.dumps(trids),
                                                         'CSCtype': data.get('type', 1),
                                                         'Detail': detail}))
        return Success('成功')

    def add_toilet(self):
        """添加厕所"""
        if common_user():
            creator = User.query.filter_by_(USid=getattr(request, 'user').id).first_('请重新登录')
            creator_id = creator.USid
            creator_type = ApplyFrom.user.value
        elif is_admin():
            creator = Admin.query.filter_by_(ADid=getattr(request, 'user').id).first_('请重新登录')
            creator_id = creator.ADid
            creator_type = ApplyFrom.platform.value
        else:
            raise TokenError('请重新登录')
        data = parameter_required({'latitude': '纬度', 'longitude': '经度', 'toimage': '图片'})
        latitude, longitude = data.get('latitude'), data.get('longitude')
        latitude, longitude = self.cplay.check_lat_and_long(latitude, longitude)
        if common_user() and latitude and longitude:
            self.BaseController.get_user_location(latitude, longitude, creator_id)
        exist = Toilet.query.filter(Toilet.isdelete == false(), Toilet.longitude == longitude,
                                    Toilet.latitude == latitude).first()
        if exist:
            raise ParamsError('该位置的厕所已被上传过')
        with db.auto_commit():
            toilet = Toilet.create({'TOid': str(uuid.uuid1()),
                                    'creatorID': creator_id,
                                    'creatorType': creator_type,
                                    'longitude': longitude,
                                    'latitude': latitude,
                                    'TOimage': data.get('toimage'),
                                    'TOstatus': ApprovalAction.submit.value
                                    })
            db.session.add(toilet)
        super(CScenicSpot, self).create_approval('totoilet', creator_id, toilet.TOid, creator_type)
        return Success('上传成功', data={'toid': toilet.TOid})

    def update_toilet(self):
        """编辑厕所"""
        if not is_admin():
            raise TokenError('请重新登录')
        data = parameter_required(('toid', 'latitude', 'longitude', 'toimage'))
        latitude, longitude = data.get('latitude'), data.get('longitude')
        latitude, longitude = self.cplay.check_lat_and_long(latitude, longitude)
        toilet = Toilet.query.filter(Toilet.isdelete == false(),
                                     Toilet.TOid == data.get('toid')).first_('未找到相应厕所信息')
        with db.auto_commit():
            if data.get('delete'):
                toilet.update({'isdelete': True})
                self.BaseAdmin.create_action(AdminActionS.delete.value, 'Toilet', toilet.TOid)
            else:
                toilet.update({'longitude': longitude,
                               'latitude': latitude,
                               'TOimage': data.get('toimage'),
                               'TOstatus': ApprovalAction.submit.value
                               })
                self.BaseAdmin.create_action(AdminActionS.update.value, 'Toilet', toilet.TOid)
            db.session.add(toilet)
            # 如果有正在进行的审批，取消
            approval_info = Approval.query.filter(Approval.AVcontent == toilet.TOid,
                                                  or_(Approval.AVstartid == toilet.creatorID,
                                                      Approval.AVstartid == getattr(request, 'user').id),
                                                  Approval.AVstatus == ApplyStatus.wait_check.value,
                                                  Approval.isdelete == false()).first()
            if approval_info:
                approval_info.AVstatus = ApplyStatus.cancle.value
        super(CScenicSpot, self).create_approval('totoilet', getattr(request, 'user').id, toilet.TOid,
                                                 ApplyFrom.platform.value)
        return Success('编辑成功', data={'toid': toilet.TOid})

    def toilet_list(self):
        """厕所列表"""
        args = request.args.to_dict()
        toilet_query = Toilet.query.filter(Toilet.isdelete == false())
        if is_admin():
            tostatus = args.get('tostatus')
            try:
                ApprovalAction(tostatus)
            except Exception as e:
                # current_app.logger.error('TOstatus error is {}'.format(e))
                tostatus = None
            if tostatus:
                toilet_query = toilet_query.filter(Toilet.TOstatus == tostatus)
            toilets = toilet_query.order_by(Toilet.createtime.desc()).all_with_page()
            for toilet in toilets:
                toilet.hide('creatorID', 'creatorType')
                toilet.fill('tostatus_zh', ApprovalAction(toilet.TOstatus).zh_value)
        else:
            parameter_required({'latitude': '请允许授权位置信息，以便为您展示附近的厕所',
                                'longitude': '请允许授权位置信息，以便为您展示附近的厕所'}, datafrom=args)
            latitude, longitude = args.get('latitude'), args.get('longitude')
            if latitude == 'null':
                raise ParamsError('请允许授权位置信息，以便为您展示附近的厕所')
            latitude, longitude = self.cplay.check_lat_and_long(latitude, longitude)
            if common_user() and latitude and longitude:
                self.BaseController.get_user_location(latitude, longitude, getattr(request, 'user').id)
            scale = args.get('scale', 14)
            variable = self.scale_dict.get(int(float(scale)))
            toilets = toilet_query.filter(Toilet.TOstatus == ApprovalAction.agree.value,
                                          Toilet.latitude <= float(latitude) + variable,
                                          Toilet.latitude >= float(latitude) - variable,
                                          Toilet.longitude <= float(longitude) + variable,
                                          Toilet.longitude >= float(longitude) - variable,
                                          ).all()
            [toilet.hide('creatorID', 'creatorType') for toilet in toilets]
        return Success(data=toilets)

    def get_toilet(self):
        """厕所详情"""
        args = parameter_required(('toid',))
        toid = args.get('toid')
        toilet = Toilet.query.filter(Toilet.isdelete == false(), Toilet.TOid == toid).first_('未找到该厕所信息')
        toilet.hide('creatorID', 'creatorType')
        toilet.fill('tostatus_zh', ApprovalAction(toilet.TOstatus).zh_value)
        return Success(data=toilet)
