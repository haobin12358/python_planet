import json
import uuid
import re
from datetime import datetime, timedelta, date
from decimal import Decimal

from flask import current_app, request
from sqlalchemy import Date
from sqlalchemy.sql.expression import false

from planet.common.chinesenum import to_chinese4
from planet.common.error_response import ParamsError, StatusError
from planet.common.params_validates import parameter_required
from planet.common.success_response import Success
from planet.common.token_handler import get_current_user, phone_required
from planet.config.enums import PlayStatus
from planet.models.user import User
from planet.models.play import Gather
from planet.extensions.register_ext import db, conn
from planet.extensions.tasks import start_play, end_play, celery
from planet.models import Cost, Insurance, Play, PlayRequire, EnterLog


class CPlay():

    def __init__(self):
        self.split_item = '!@##@!'
        self.connect_item = '-'

    @phone_required
    def set_play(self):
        data = parameter_required()
        plid = data.get('plid')
        with db.auto_commit():
            if plid:
                play = Play.query.filter_by(PLid=plid, isdelete=False).first()
                if not play:
                    raise ParamsError('参数缺失')
                if play.PLstatus == PlayStatus.activity.value:
                    raise StatusError('进行中活动无法修改')

                if data.get('delete'):
                    current_app.logger.info('删除活动 {}'.format(plid))
                    play.isdelete = True
                    db.session.add(play)
                    return Success('删除成功', data=plid)
                update_dict = self._get_update_dict(play, data)
                if update_dict.get('PLlocation'):
                    update_dict.update(PLlocation=self.split_item.join(update_dict.get('PLlocation')))
                if update_dict.get('PLproducts'):
                    update_dict.update(PLproducts=self.split_item.join(update_dict.get('PLproducts')))
                if update_dict.get('PLcreate'):
                    update_dict.pop('PLcreate')
                if update_dict.get('PLcontent'):
                    update_dict.update(PLcontent=json.dumps(update_dict.get('PLcontent')))
                playname = {
                    'pllocation': update_dict.get('PLlocation') or play.PLlocation,
                    'plstarttime': update_dict.get('PLstarttime') or play.PLstartTime,
                    'plendtime': update_dict.get('PLendTime') or play.PLendTime,
                }
                plname = self._update_plname(playname)
                update_dict.update(PLname=plname)
                play.update(update_dict)
                db.session.add(play)
                self._update_cost_and_insurance(data, plid)
                self.auto_playstatus(play)
                return Success('更新成功', data=plid)
            data = parameter_required(
                ('plimg', 'plstarttime', 'plendtime', 'pllocation', 'plnum', 'pltitle', 'plcontent'))
            plid = str(uuid.uuid1())
            plname = self._update_plname(data)
            play = Play.create({
                'PLid': plid,
                'PLimg': data.get('plimg'),
                'PLstartTime': data.get('plstarttime'),
                'PLendTime': data.get('plendtime'),
                'PLlocation': self.split_item.join(data.get('pllocation')),
                'PLnum': int(data.get('plnum')),
                'PLtitle': data.get('pltitle'),
                'PLcontent': json.dumps(data.get('plcontent')),
                'PLcreate': request.user.id,
                'PLstatus': PlayStatus(int(data.get('plstatus', 0))).value,
                'PLname': plname,
                'PLproducts': self.split_item.join(data.get('plproducts')),
            })
            db.session.add(play)
            self._update_cost_and_insurance(data, plid)

            self.auto_playstatus(play)
        return Success(data=plid)

    @phone_required
    def set_cost(self):
        data = parameter_required(('costs',))
        with db.auto_commit():
            costs = data.get('costs')
            instance_list = list()
            cosid_list = list()
            for cost in costs:
                current_app.logger.info('get cost {}'.format(cost))
                cosid = cost.get('cosid')
                if cost.get('delete'):
                    cost_instance = Cost.query.filter_by(COSid=cosid, isdelete=False).first()
                    if not cost_instance:
                        continue
                    if self._check_activity_play(cost_instance):
                        raise StatusError('进行中活动无法修改')
                    # return Success('删除成功')
                    cost_instance.isdelete = True
                    instance_list.append(cost_instance)
                    current_app.logger.info('删除费用 {}'.format(cosid))
                    continue

                subtotal = Decimal(str(cost.get('cossubtotal')))
                if subtotal < Decimal('0'):
                    subtotal = Decimal('0')

                if cosid:
                    cost_instance = Cost.query.filter_by(COSid=cosid, isdelete=False).first()
                    if cost_instance:
                        if self._check_activity_play(cost_instance):
                            raise StatusError('进行中活动无法修改')
                        update_dict = self._get_update_dict(cost_instance, cost)
                        if update_dict.get('COSsubtotal'):
                            update_dict.update(COSsubtotal=subtotal)
                        cost_instance.update(update_dict)
                        instance_list.append(cost_instance)
                        cosid_list.append(cosid)
                        continue
                cosid = str(uuid.uuid1())
                cost_instance = Cost.create({
                    "COSid": cosid,
                    "COSname": cost.get('cosname'),
                    "COSsubtotal": subtotal,
                    "COSdetail": cost.get('cosdetail'),
                })
                instance_list.append(cost_instance)
                cosid_list.append(cosid)
            db.session.add_all(instance_list)

        return Success(data=cosid_list)

    def get_cost(self):
        data = parameter_required()
        plid = data.get('plid')
        if not plid:
            return Success(data=list())
        costs_list = Cost.query.filter_by(PLid=plid, isdelete=False).order_by(Cost.createtime.asc()).all()
        return Success(data=costs_list)

    @phone_required
    def set_insurance(self):
        data = parameter_required()
        with db.auto_commit():
            insurance_list = data.get('insurance')
            instance_list = list()
            inid_list = list()
            for ins in insurance_list:
                current_app.logger.info('get Insurance {} '.format(ins))
                inid = data.get('inid')
                incost = Decimal(str(data.get('incost', '0')))
                if incost < Decimal('0'):
                    incost = Decimal('0')

                if data.get('delete'):
                    current_app.logger.info('删除 Insurance {} '.format(inid))
                    ins_instance = Insurance.query.filter_by(INid=inid, isdelete=False).first()
                    if not instance_list:
                        continue
                    if self._check_activity_play(ins_instance):
                        raise StatusError('进行中活动无法修改')
                    continue

                if inid:
                    ins_instance = Insurance.query.filter_by(INid=inid, isdelete=False).first()
                    if ins_instance:
                        if self._check_activity_play(ins_instance):
                            raise StatusError('进行中活动无法修改')
                        update_dict = self._get_update_dict(ins_instance, ins)
                        if update_dict.get('INcost'):
                            update_dict.update(INcost=incost)
                        ins_instance.update()
                        instance_list.append(ins_instance)
                        inid_list.append(inid)
                        continue
                inid = str(uuid.uuid1())
                ins_instance = Insurance.create({
                    'INid': inid,
                    'INname': ins.get('inname'),
                    'INcontent': ins.get('incontent'),
                    'INtype': int(ins.get('intype')),
                    'INcost': incost,
                })
                instance_list.append(ins_instance)
                inid_list.append(inid)
            db.session.add_all(instance_list)
        return Success(data=inid_list)

    def get_insurance(self):
        data = parameter_required()
        plid = data.get('plid')
        if not plid:
            return Success(data=list())
        ins_list = Insurance.query.filter_by(PLid=plid, isdelete=False).order_by(Insurance.createtime.asc()).all()
        return Success(data=ins_list)

    def get_play(self):
        data = parameter_required(('plid',))
        plid = data.get('plid')
        play = Play.query.filter_by(PLid=plid, isdelete=False).first_('活动已删除')
        self._fill_play(play)
        self._fill_costs(play)
        self._fill_insurances(play)
        return Success(data=play)

    def get_play_list(self):
        data = parameter_required()
        user = get_current_user()
        join_or_create = int(data.get('playtype', 0))

        filter_args = set()
        filter_args.add(Play.isdelete == False)
        if data.get('createtime'):
            createtime = data.get('createtime')
            try:
                if isinstance(createtime, str):
                    createtime = datetime.strptime(createtime, '%Y-%m-%d').date()
                elif isinstance(createtime, datetime):
                    createtime = createtime.date()
            except:
                current_app.logger.info('时间筛选格式不对 时间 {} 类型{}'.format(createtime, type(createtime)))
                raise ParamsError

            filter_args.add(Play.createtime.cast(Date) == createtime)
        if data.get('plstatus') or data.get('plstatus') == 0:
            try:
                filter_args.add(Play.PLstatus == PlayStatus(int(data.get('plstatus'))).value)
            except:
                current_app.logger.info('状态筛选数据不对 状态{}'.format(data.get('plstatus')))
                raise ParamsError
        if join_or_create:
            filter_args.add(EnterLog.USid == user.USid)
            filter_args.add(EnterLog.isdelete == False)
            plays_list = Play.query.join(EnterLog, EnterLog.PLid == Play.PLid).filter(*filter_args).order_by(
                Play.createtime.desc()).all_with_page()
        else:
            plays_list = Play.query.filter(Play.PLcreate == user.USid, *filter_args).order_by(
                Play.createtime.desc()).all_with_page()
        for play in plays_list:
            self._fill_play(play)

        return Success(data=plays_list)

    def get_all_play(self):
        data = parameter_required()
        plstatus = data.get('plstatus')
        filter_args = {
            Play.isdelete == False
        }
        # order_args = {
        #
        # }
        if plstatus is not None:
            filter_args.add(Play.PLstatus == int(plstatus))
        # if

        plays_list = Play.query.filter(*filter_args).order_by(
            Play.createtime.desc()).all_with_page()
        for play in plays_list:
            self._fill_play(play)

        return Success(data=plays_list)

    def auto_playstatus(self, play):
        if play.PLstatus == PlayStatus.publish.value:
            start_connid = 'startplay{}'.format(play.PLid)
            end_connid = 'endplay{}'.format(play.PLid)
            self._cancle_celery(start_connid)
            self._cancle_celery(end_connid)
            starttime = play.PLstartTime
            endtime = play.PLendTime
            if not isinstance(starttime, datetime):
                starttime = datetime.strptime(starttime, '%Y-%m-%d %H:%M')
            if not isinstance(endtime, datetime):
                endtime = datetime.strptime(endtime, '%Y-%m-%d %H:%M')
            start_task_id = start_play.apply_async(args=(play.PLid,), eta=starttime - timedelta(hours=8))
            end_task_id = end_play.apply_async(args=(play.PLid,), eta=endtime - timedelta(hours=8))
            conn.set(start_connid, start_task_id)
            conn.set(end_connid, end_task_id)

    @phone_required
    def get_gather(self):
        """查看集合点"""
        args = request.args.to_dict()
        my_lat, my_long = args.get('latitude'), args.get('longitude')
        my_lat, my_long = self.check_lat_and_long(my_lat, my_long)
        now = datetime.now()
        user = User.query.filter_by_(USid=getattr(request, 'user').id).first_('请重新登录')
        can_post, gather_location, my_location, res = False, None, None, []
        if my_lat and my_long:
            my_location = self.init_location_dict(my_lat, my_long, '我的位置')
        my_created_play = Play.query.filter(Play.isdelete == false(),
                                            Play.PLstatus == PlayStatus.activity.value,
                                            Play.PLstartTime <= now,
                                            Play.PLendTime >= now,
                                            Play.PLcreate == user.USid).first()
        my_joined_play = EnterLog.query.join(Play, Play.PLid == EnterLog.PLid
                                             ).filter(Play.isdelete == false(),
                                                      Play.PLstatus == PlayStatus.activity.value,
                                                      Play.PLstartTime <= now,
                                                      Play.PLendTime >= now,
                                                      EnterLog.isdelete == false(),
                                                      EnterLog.USid == user.USid,
                                                      EnterLog.ELstatus == '已通过的报名状态'
                                                      ).first()
        if my_created_play:  # 是领队，显示上次定位点，没有为null
            can_post = True
            last_anchor_point = Gather.query.filter(Gather.isdelete == false(),
                                                    Gather.PLid == my_created_play.PLid,
                                                    Gather.GAcreate == user.USid
                                                    ).order_by(Gather.createtime.desc()).first()
            if last_anchor_point:
                gather_location = self.init_location_dict(last_anchor_point.GAlat,
                                                          last_anchor_point.GAlon,
                                                          '上次集合 {}'.format(last_anchor_point.GAtime)[11:16])
        else:  # 非领队
            if my_joined_play:  # 存在参加的进行中的活动
                gather_point = Gather.query.filter(Gather.isdelete == false(),
                                                   Gather.PLid == my_joined_play.PLid,
                                                   ).order_by(Gather.createtime.desc()).first()
                gather_location = self.init_location_dict(gather_point.GAlat,
                                                          gather_point.GAlon,
                                                          str(gather_point.GAtime)[11:16])

        res = {'gather_location': gather_location, 'my_location': my_location, 'can_post': can_post}
        return Success(data=res)

    @staticmethod
    def init_location_dict(latitude, longitude, content):
        res = {
            'latitude': latitude,
            'longitude': longitude,
            'content': content
        }
        return res

    @staticmethod
    def check_lat_and_long(lat, long):
        try:
            if not -90 <= float(lat) <= 90:
                raise ParamsError('纬度错误，范围 -90 ~ 90')
            if not -180 <= float(long) <= 180:
                raise ParamsError('经度错误，范围 -180 ~ 180')
        except (TypeError, ValueError):
            raise ParamsError('经纬度应为合适范围内的浮点数')
        return float(lat), float(long)

    @phone_required
    def set_gather(self):
        """发起集合点"""
        data = phone_required(('latitude', 'longitude', 'time'))
        latitude, longitude, time = data.get('latitude'), data.get('longitude'), data.get('time')
        if not re.match(r'^\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}$', str(time)):
            raise ParamsError('集合时间格式错误')
        latitude, longitude = self.check_lat_and_long(latitude, longitude)
        now = datetime.now()
        user = User.query.filter_by_(USid=getattr(request, 'user').id).first_('请重新登录')
        my_created_play = Play.query.filter(Play.isdelete == false(),
                                            Play.PLstatus == PlayStatus.activity.value,
                                            Play.PLstartTime <= now,
                                            Play.PLendTime >= now,
                                            Play.PLcreate == user.USid).first()
        if not my_created_play:
            raise StatusError('您没有正在进行的活动')
        with db.auto_commit():
            gather_instance = Gather.create({
                'GAid': str(uuid.uuid1()),
                'PLid': my_created_play.PLid,
                'GAlon': longitude,
                'GAlat': latitude,
                'GAcreate': user.USid,
                'GAtime': time
            })
            db.session.add(gather_instance)
        return Success('创建成功', {'latitude': latitude, 'longitude': longitude, 'time': str(time)[11:16]})

    def _cancle_celery(self, conid):
        exist_task = conn.get(conid)
        if exist_task:
            exist_task = str(exist_task, encoding='utf-8')
            current_app.logger.info('已有任务id: {}'.format(exist_task))
            celery.AsyncResult(exist_task).revoke()

    def _update_cost_and_insurance(self, data, plid):
        instance_list = list()
        error_dict = {'costs': list(), 'insurances': list(), 'playrequires': list()}

        costs_list = data.get('costs') or list()
        ins_list = data.get('insurances') or list()
        prs_list = data.get('playrequires') or list()
        for costid in costs_list:
            cost = Cost.query.filter_by(COSid=costid, isdelete=False).first()
            if not cost:
                error_dict.get('costs').append(costid)
                continue
            cost.update({"PLid": plid})
            instance_list.append(cost)
        for inid in ins_list:
            insurance = Insurance.query.filter_by(INid=inid, isdelete=False).first()
            if not insurance:
                error_dict.get('insurances').append(inid)
                continue
            insurance.update({"PLid": plid})
            instance_list.append(insurance)

        presort = 1
        preid_list = list()
        for prename in prs_list:

            pre = PlayRequire.query.filter_by(PREname=prename, PLid=plid, isdelete=False).first()
            if pre:
                pre.update({'PLid': plid, 'PREsort': presort})
            else:
                pre = PlayRequire.create({
                    'PREid': str(uuid.uuid1()),
                    'PREname': prename,
                    'PLid': plid,
                    'PREsort': presort
                })
            preid_list.append(pre.PREid)
            instance_list.append(pre)
            presort += 1

        PlayRequire.query.filter(
            PlayRequire.PLid == plid,
            PlayRequire.PREid.notin_(preid_list),
            PlayRequire.isdelete == False
        ).delete_(synchronize_session=False)
        db.session.add_all(instance_list)
        current_app.logger.info('the error in this updating {}'.format(error_dict))

    def _update_plname(self, data):
        pllocation = data.get('pllocation')
        if isinstance(data.get('pllocation'), list):
            pllocation = self.connect_item.join(data.get('pllocation'))

        try:
            plstart = data.get('plstarttime')
            plend = data.get('plendtime')
            if not isinstance(plstart, datetime):
                plstart = datetime.strptime(data.get('plstarttime'), '%Y-%m-%d %H:%M')

            if not isinstance(plend, datetime):
                plend = datetime.strptime(data.get('plendtime'), '%Y-%m-%d %H:%M')
        except:
            current_app.logger.error('转时间失败  开始时间 {}  结束时间 {}'.format(data.get('plstarttime'), data.get('plendtime')))
            raise ParamsError
        duraction = plend - plstart
        if duraction.days < 0:
            current_app.logger.error('起止时间有误')
            raise ParamsError
        days = to_chinese4(duraction.days)
        plname = '{}·{}日'.format(pllocation, days)
        return plname

    def _check_activity_play(self, check_model):
        # if not check_model:
        #     raise ParamsError('参数缺失')
        play = Play.query.filter_by(PLid=check_model.PLid, isdelete=False).first()
        if play and play.PLstatus == PlayStatus.activity.value:
            return True
        return False

    def _get_update_dict(self, instance_model, data_model):
        update_dict = dict()
        for key in instance_model.keys():
            lower_key = str(key).lower()
            if data_model.get(lower_key) or data_model.get(lower_key) == 0:
                update_dict.setdefault(key, data_model.get(lower_key))
        return update_dict

    def _fill_play(self, play):
        play.hide('PLcreate')
        play.fill('PLlocation', str(play.PLlocation).split(self.split_item))
        play.fill('PLproducts', str(play.PLproducts).split(self.split_item))
        play.fill('PLcontent', json.loads(play.PLcontent))
        play.fill('plstatus_zh', PlayStatus(play.PLstatus).zh_value)
        play.fill('plstatus_en', PlayStatus(play.PLstatus).name)
        playrequires = PlayRequire.query.filter_by(PLid=play.PLid, isdelete=False).order_by(
            PlayRequire.PREsort.asc()).all()

        play.fill('playrequires', [playrequire.PREname for playrequire in playrequires])

    def _fill_costs(self, play):
        costs_list = Cost.query.filter_by(PLid=play.PLid, isdelete=False).order_by(Cost.createtime.asc()).all()
        playsum = getattr(play, 'playsum', 0)
        costsum = sum([cost.COSsubtotal for cost in costs_list])
        playsum = Decimal(str(playsum)) + costsum
        play.fill('costs', costs_list)
        play.fill('playsum', playsum)

    def _fill_insurances(self, play):
        ins_list = Insurance.query.filter_by(PLid=play.PLid, isdelete=False).order_by(Insurance.createtime.asc()).all()
        playsum = getattr(play, 'playsum', 0)
        inssum = sum([ins.INcost for ins in ins_list])
        playsum = Decimal(str(playsum)) + inssum
        play.fill('insurances', ins_list)
        play.fill('playsum', playsum)

    @phone_required
    def join(self):
        data = parameter_required(('plid', ))
        plid = data.get('plid')
        costs = data.get('costs')
        insurances = data.get('insurances')
        for cost in costs:
            cost_model = Cost.query.filter(Cost.COSid == cost.get('cosid'), Cost.isdelete == False,).first()
            if not cost_model:
                raise ParamsError

        for insurance in insurances:
            pass
