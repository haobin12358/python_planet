# 小程序 用来创建活动 管理活动
import json
import uuid
from datetime import datetime
from decimal import Decimal

from flask import current_app, request

from planet.common.chinesenum import to_chinese4
from planet.common.error_response import ParamsError, StatusError
from planet.common.params_validates import parameter_required
from planet.common.success_response import Success
from planet.common.token_handler import get_current_user
from planet.config.enums import PlayStatus
from planet.extensions.register_ext import db
from planet.models import Cost, Insurance, Play


class CPlay():

    def __init__(self):
        self.split_item = '!@##@!'
        self.connect_item = '-'

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
                if update_dict.get('PLproducts'):
                    update_dict.update(PLproducts=self.split_item.join(update_dict.get('PLproducts')))
                if update_dict.get('PLcreate'):
                    update_dict.pop('PLcreate')

                play.update(update_dict)
                db.session.add(play)
                self._update_cost_and_insurance(data, plid)
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
        return Success(data=plid)

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

    def set_insurance(self):
        data = parameter_required()
        with db.auto_commit():
            insurance_list = data.get('insurance')
            instance_list = list()
            inid_list = list()
            for ins in insurance_list:
                current_app.logger.info('get Insurance {} '.format(ins))
                inid = data.get('inid')
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
                        ins_instance.update(self._get_update_dict(ins_instance, ins))
                        instance_list.append(ins_instance)
                        inid_list.append(inid)
                        continue
                inid = str(uuid.uuid1())
                ins_instance = Insurance.create({
                    'INid': inid,
                    'INname': ins.get('inname'),
                    'INcontent': ins.get('incontent'),
                    'INtype': int(ins.get('intype')),
                    'INcost': Decimal(ins.get('incost')),
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

    def _update_cost_and_insurance(self, data, plid):
        instance_list = list()
        error_dict = {'costs': list(), 'insurances': list()}

        costs_list = data.get('costs')
        ins_list = data.get('insurances')
        for costid in costs_list:
            cost = Cost.query.filter_by(COSid=costid, isdelete=False).first()
            if not cost:
                error_dict.get('costs').append(costid)
                continue
            cost.update(PLid=plid)
            instance_list.append(cost)
        for inid in ins_list:
            insurance = Insurance.query.filter_by(INid=inid, isdelete=False).first()
            if not insurance:
                error_dict.get('insurances').append(inid)
                continue
            insurance.update(PLid=plid)
            instance_list.append(insurance)
        db.session.add_all(instance_list)
        current_app.logger.info('the error in this updating {}'.format(error_dict))

    def _update_plname(self, data):
        pllocation = self.connect_item.join(data.get('pllocation'))
        try:
            plstart = datetime.strptime(data.get('plstarttime'), '%Y-%m-%d %H:%M:%S')
            plend = datetime.strptime(data.get('plendtime'), '%Y-%m-%d %H:%M:%S')
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

    def get_play(self):
        data = parameter_required(('plid',))
        plid = data.get('plid')
        play = Play.query.filter_by(PLid=plid, isdelete=False).first_('活动已删除')
        self._fill_play(play)
        self._fill_costs(play)
        self._fill_insurances(play)
        return Success(data=play)

    def _fill_play(self, play):
        play.hide('PLcreate')
        play.fill('PLlocation', str(play.PLlocation).split(self.split_item))
        play.fill('PLproducts', str(play.PLproducts).split(self.split_item))
        play.fill('PLcontent', json.loads(play.PLcontent))
        play.fill('plstatus_zh', PlayStatus(play.PLstatus).zh_value)
        play.fill('plstatus_en', PlayStatus(play.PLstatus).name)

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

    def get_play_list(self):
        user = get_current_user()
        plays_list = Play.query.filter_by(PLcreate=user.USid, isdelete=False).order_by(
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
            filter_args.add(Play.PLstatus == plstatus)
        # if

        plays_list = Play.query.filter(*filter_args).order_by(
            Play.createtime.desc()).all_with_page()
        for play in plays_list:
            self._fill_play(play)

        return Success(data=plays_list)
