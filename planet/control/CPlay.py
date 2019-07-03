import json
import random
import uuid
import re
from datetime import datetime, timedelta
from decimal import Decimal

from flask import current_app, request
from sqlalchemy import Date, or_, and_, false

from planet.common.chinesenum import to_chinese4
from planet.common.error_response import ParamsError, StatusError, AuthorityError
from planet.common.params_validates import parameter_required
from planet.common.success_response import Success
from planet.common.token_handler import get_current_user, phone_required, common_user

from planet.config.enums import PlayStatus, EnterCostType, EnterLogStatus, PayType, Client, OrderFrom, SigninLogStatus
from planet.config.http_config import API_HOST

from planet.control.BaseControl import BaseController
from planet.extensions.register_ext import db, conn, mini_wx_pay

from planet.extensions.tasks import start_play, end_play, celery
from planet.extensions.weixin.pay import WeixinPayError
from planet.models import Cost, Insurance, Play, PlayRequire, EnterLog, EnterCost, User, Gather, SignInSet, \
    SignInLog


class CPlay():

    def __init__(self):
        # super(CPlay, self).__init__()
        self.wx_pay = mini_wx_pay
        self.split_item = '!@##@!'
        self.connect_item = '-'
        self.basecontrol = BaseController()
        self.guidelevel = 5

    def _pay_detail(self, body, mount_price, opayno, openid):
        body = re.sub("[\s+\.\!\/_,$%^*(+\"\'\-_]+|[+——！，。？、~@#￥%……&*（）]+", '', body)
        current_app.logger.info('get mount price {}'.format(mount_price))
        mount_price = 0.01 if API_HOST != 'https://www.bigxingxing.com' else mount_price
        current_app.logger.info('openid is {}, out_trade_no is {} '.format(openid, opayno))
        # 微信支付的单位是'分', 支付宝使用的单位是'元'

        try:
            body = body[:16] + '...'
            current_app.logger.info('body is {}, wechatpay'.format(body))
            wechat_pay_dict = {
                'body': body,
                'out_trade_no': opayno,
                'total_fee': int(mount_price * 100),
                'attach': 'attach',
                'spbill_create_ip': request.remote_addr
            }

            if not openid:
                raise StatusError('用户未使用微信登录')
            # wechat_pay_dict.update(dict(trade_type="JSAPI", openid=openid))
            wechat_pay_dict.update({
                'trade_type': 'JSAPI',
                'openid': openid
            })
            raw = self.wx_pay.jsapi(**wechat_pay_dict)

        except WeixinPayError as e:
            raise SystemError('微信支付异常: {}'.format('.'.join(e.args)))

        return raw

    @phone_required
    def set_play(self):
        data = parameter_required()
        plid = data.get('plid')
        # todo  增加用户状态判断
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
                'PLlocation': self.split_item.join(data.get('pllocation', [])),
                'PLnum': int(data.get('plnum')),
                'PLtitle': data.get('pltitle'),
                'PLcontent': json.dumps(data.get('plcontent')),
                'PLcreate': request.user.id,
                'PLstatus': PlayStatus(int(data.get('plstatus', 0))).value,
                'PLname': plname,
                'PLproducts': self.split_item.join(data.get('plproducts', [])),
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
                        if update_dict.get('COSdetail'):
                            update_dict.update(COSdetail=json.dumps(update_dict.get('COSdetail')))
                        cost_instance.update(update_dict)
                        instance_list.append(cost_instance)
                        cosid_list.append(cosid)
                        continue
                cosid = str(uuid.uuid1())
                cost_instance = Cost.create({
                    "COSid": cosid,
                    "COSname": cost.get('cosname'),
                    "COSsubtotal": subtotal,
                    "COSdetail": json.dumps(cost.get('cosdetail')),
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
        for cost in costs_list:
            cost.fill('COSdetail', json.loads(cost.COSdetail))

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
                inid = ins.get('inid')
                incost = Decimal(str(ins.get('incost', '0')))
                if incost < Decimal('0'):
                    incost = Decimal('0')
                current_app.logger.info(' changed insurance cost = {}'.format(incost))
                if ins.get('delete'):
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
            self._fill_costs(play, show=False)
            self._fill_insurances(play, show=False)
        return Success(data=plays_list)

    def get_all_play(self):
        data = parameter_required()
        plstatus = data.get('plstatus')
        filter_args = {
            Play.isdelete == False
        }

        if plstatus is not None:
            filter_args.add(Play.PLstatus == int(plstatus))
        # if

        plays_list = Play.query.filter(*filter_args).order_by(
            Play.createtime.desc()).all_with_page()
        for play in plays_list:
            self._fill_play(play)
            self._fill_costs(play)
            self._fill_insurances(play)
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
                starttime = self._trans_time(starttime)
            if not isinstance(endtime, datetime):
                endtime = self._trans_time(endtime)
            start_task_id = start_play.apply_async(args=(play.PLid,), eta=starttime - timedelta(hours=8))
            end_task_id = end_play.apply_async(args=(play.PLid,), eta=endtime - timedelta(hours=8))
            conn.set(start_connid, start_task_id)
            conn.set(end_connid, end_task_id)

    @phone_required
    def identity(self):
        """身份判断"""
        user = User.query.filter_by_(USid=getattr(request, 'user').id).first_('请重新登录')
        is_leader = self._is_tourism_leader(user.USid)
        return Success(data={'is_leader': bool(is_leader)})

    @staticmethod
    def _is_tourism_leader(usid):
        """是否是领队"""
        if not usid:
            return
        now = datetime.now()
        return Play.query.filter(Play.isdelete == false(),
                                 Play.PLstatus == PlayStatus.activity.value,
                                 Play.PLstartTime <= now,
                                 Play.PLendTime >= now,
                                 Play.PLcreate == usid).first()

    @staticmethod
    def _ongoing_play_joined(usid):
        """是否有正在参加的活动"""
        if not usid:
            return
        now = datetime.now()
        return EnterLog.query.join(Play, Play.PLid == EnterLog.PLid
                                   ).filter(Play.isdelete == false(),
                                            Play.PLstatus == PlayStatus.activity.value,
                                            Play.PLstartTime <= now,
                                            Play.PLendTime >= now,
                                            EnterLog.isdelete == false(),
                                            EnterLog.USid == usid,
                                            EnterLog.ELstatus == EnterLogStatus.success.value,
                                            ).first()

    @phone_required
    def help(self):
        """一键求救"""
        user = User.query.filter_by_(USid=getattr(request, 'user').id).first_('请重新登录')
        data = request.json
        latitude, longitude = data.get('latitude'), data.get('longitude')
        latitude, longitude = self.check_lat_and_long(latitude, longitude)
        self.basecontrol.get_user_location(latitude, longitude, user.USid)
        pass

    @phone_required
    def get_gather(self):
        """查看集合点"""
        args = request.args.to_dict()
        my_lat, my_long = args.get('latitude'), args.get('longitude')
        my_lat, my_long = self.check_lat_and_long(my_lat, my_long)
        user = User.query.filter_by_(USid=getattr(request, 'user').id).first_('请重新登录')
        can_post, gather_location, my_location = False, None, None
        button_name = '暂无活动'
        if my_lat and my_long:
            self.basecontrol.get_user_location(my_lat, my_long, user.USid)  # 记录位置
        my_created_play = self._is_tourism_leader(user.USid)

        if my_created_play:  # 是领队，显示上次定位点，没有为null
            can_post = True
            button_name = '发起集合'
            last_anchor_point = Gather.query.filter(Gather.isdelete == false(),
                                                    Gather.PLid == my_created_play.PLid,
                                                    Gather.GAcreate == user.USid
                                                    ).order_by(Gather.createtime.desc()).first()
            if last_anchor_point:
                gather_location = self.init_location_dict(last_anchor_point.GAlat,
                                                          last_anchor_point.GAlon,
                                                          '上次集合 {}'.format(str(last_anchor_point.GAtime)[11:16]))
        else:  # 非领队
            my_joined_play = self._ongoing_play_joined(user.USid)
            if my_joined_play:  # 存在参加的进行中的活动
                button_name = '等待集合'
                gather_point = Gather.query.filter(Gather.isdelete == false(),
                                                   Gather.PLid == my_joined_play.PLid,
                                                   ).order_by(Gather.createtime.desc()).first()
                gather_location = self.init_location_dict(gather_point.GAlat,
                                                          gather_point.GAlon,
                                                          str(gather_point.GAtime)[11:16])

        res = {'gather_location': gather_location,
               'can_post': can_post, 'button_name': button_name}

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
        return str(lat), str(long)

    @phone_required
    def set_gather(self):
        """发起集合点"""
        data = parameter_required(('latitude', 'longitude', 'time'))
        latitude, longitude, time = data.get('latitude'), data.get('longitude'), data.get('time')
        if not re.match(r'^[0-2][0-9]:[0-6][0-9]$', str(time)):
            raise ParamsError('集合时间格式错误')
        now = datetime.now()
        user = User.query.filter_by_(USid=getattr(request, 'user').id).first_('请重新登录')
        gather_time = str(now)[0:11] + str(time) + ':00'
        gather_time = datetime.strptime(gather_time, '%Y-%m-%d %H:%M:%S')
        latitude, longitude = self.check_lat_and_long(latitude, longitude)
        if latitude and longitude:
            self.basecontrol.get_user_location(latitude, longitude, user.USid)
        my_created_play = Play.query.filter(Play.isdelete == false(),
                                            Play.PLstatus == PlayStatus.activity.value,
                                            Play.PLstartTime <= now,
                                            Play.PLendTime >= now,
                                            Play.PLcreate == user.USid).first()
        if not my_created_play:
            raise StatusError('您没有正在进行的活动')
        if not (my_created_play.PLstartTime <= gather_time <= my_created_play.PLendTime):
            raise ParamsError('集合时间不在活动时间范围内')

        with db.auto_commit():
            gather_instance = Gather.create({
                'GAid': str(uuid.uuid1()),
                'PLid': my_created_play.PLid,
                'GAlon': longitude,
                'GAlat': latitude,
                'GAcreate': user.USid,
                'GAtime': gather_time
            })
            db.session.add(gather_instance)
        return Success('创建成功', {'latitude': latitude, 'longitude': longitude, 'time': time})

    def get_playrequire(self):
        data = parameter_required(('plid',))
        pre_list = PlayRequire.query.filter(PlayRequire.PLid == data.get('plid'), PlayRequire.isdelete == False) \
            .order_by(PlayRequire.PREsort.asc(), PlayRequire.createtime.desc()).all()
        return Success(data=pre_list)

    @phone_required
    def join(self):
        data = parameter_required(('plid',))
        plid = data.get('plid')
        elid = data.get('elid')
        opayno = self.wx_pay.nonce_str
        play = Play.query.filter_by(PLid=plid, isdelete=False).first_('活动已删除')
        user = get_current_user()

        with db.auto_commit():
            if self._check_plid(user, play):
                raise StatusError('同一时间只能参加一个活动')

            if elid:
                el = EnterLog.query.filter_by(ELid=elid, isdelete=False).first()
                if el:
                    # 校验修改
                    if el.PLid != plid:
                        raise ParamsError('同一时间只能参加一个活动')
                    # 更新费用明细
                    self._update_enter_cost(el, data)
                    if data.get('elvalue'):
                        elvalue = self._update_elvalue(plid, data)
                        el.update({'ELvalue': json.dumps(elvalue)})
                    el.ELpayNo = opayno

                    db.session.add(el)
                    # return Success('修改成功')
                else:
                    elid = str(uuid.uuid1())
                    elvalue = self._update_elvalue(plid, data)
                    el = EnterLog.create({
                        'ELid': elid,
                        'PLid': plid,
                        'USid': user.USid,
                        'ELstatus': EnterLogStatus.wait_pay.value,
                        'ELpayNo': opayno,
                        'ELvalue': json.dumps(elvalue)
                    })
                    db.session.add(el)
                    self._update_enter_cost(el, data)

            else:

                elid = str(uuid.uuid1())
                elvalue = self._update_elvalue(plid, data)
                el = EnterLog.create({
                    'ELid': elid,
                    'PLid': plid,
                    'USid': user.USid,
                    'ELstatus': EnterLogStatus.wait_pay.value,
                    'ELpayNo': opayno,
                    'ELvalue': json.dumps(elvalue)
                })
                db.session.add(el)
                self._update_enter_cost(el, data)

        body = play.PLname
        openid = user.USopenid1

        mount_price = sum(
            [ec.ECcost for ec in EnterCost.query.filter(EnterCost.ELid == elid, EnterCost.isdelete == false()).all()])
        try:
            omclient = int(data.get('omclient', Client.wechat.value))  # 下单设备
            omfrom = int(data.get('omfrom', OrderFrom.product_info.value))  # 商品来源
            Client(omclient)
            OrderFrom(omfrom)
        except Exception as e:
            raise ParamsError('客户端或商品来源错误')

        pay_args = self._pay_detail(body, float(mount_price), opayno, openid)

        response = {
            'pay_type': PayType.wechat_pay.name,
            'opaytype': PayType.wechat_pay.value,
            'elid': elid,
            'args': pay_args
        }
        return Success(data=response)

    @phone_required
    def get_enterlog(self):
        user = get_current_user()
        data = parameter_required(('plid',))
        plid = data.get('plid')
        el = EnterLog.query.filter(
            EnterLog.USid == user.USid, EnterLog.PLid == plid, EnterLog.isdelete == false()).first()
        play = Play.query.filter(Play.PLid == plid, Play.isdelete == false()).first_('活动已删除')
        ec_list = EnterCost.query.filter(EnterCost.ELid == el.ELid, EnterCost.isdelete == false()).all()

        self._fill_play(play)
        play.fill('elid', el.ELid)
        play.fill('ELvalue', json.loads(el.ELvalue))
        play.fill('elstatus', el.ELstatus)
        play.fill('elstatus_zh', EnterLogStatus(el.ELstatus).zh_value)
        play.fill('elstatus_en', EnterLogStatus(el.ELstatus).name)
        for ec in ec_list:
            if ec.ECtype == EnterCostType.cost.value:
                cost = Cost.query.filter(Cost.COSid == ec.ECcontent, Cost.isdelete == false()).first()
                if not cost:
                    continue
                ec.fill('ecname', cost.COSname)
            else:
                insruance = Insurance.query.filter(Insurance.INid == ec.ECcontent,
                                                   Insurance.isdelete == false()).first()
                if not insruance:
                    continue
                ec.fill('ecname', insruance.INname)
        play.fill('cost_list', ec_list)

        return Success(data=play)

    @phone_required
    def set_signin(self):
        data = parameter_required(('plid',))
        plid = data.get('plid')
        user = get_current_user()
        with db.auto_commit():
            play = Play.query.filter(Play.PLid == plid, Play.isdelete == false()).first()

            if not play or play.PLstatus != PlayStatus.activity.value:
                raise StatusError('当前活动尚未开启不能签到')
            if play.PLcreate != user.USid:
                raise AuthorityError('只能发起自己创建的活动的签到')

            SignInSet.query.filter(SignInSet.PLid == plid, SignInSet.isdelete == false()).delete_(
                synchronize_session=False)

            sis = SignInSet.create({
                'SISid': str(uuid.uuid1()),
                'PLid': plid,
                'SILnum': self._random_num()
            })
            db.session.add(sis)
            els = EnterLog.query.filter(EnterLog.ELstatus == EnterLogStatus.success.value, EnterLog.PLid == plid,
                                        EnterLog.isdelete == false()).all()
            instance_list = list()
            for enter in els:
                sil = SignInLog.create({
                    'SILid': str(uuid.uuid1()),
                    'SISid': sis.SISid,
                    'USid': enter.USid,
                    'SISstatus': SigninLogStatus.wait.value
                })
                instance_list.append(sil)
            db.session.add_all(instance_list)
        return Success(data=sis)

    def get_signin(self):
        data = parameter_required(('plid',))
        plid = data.get('plid')
        sis = SignInSet.query.filter(SignInSet.PLid == plid, SignInSet.isdelete == false()).order_by(
            SignInSet.createtime.desc()).first_('签到已失效')

        sils = SignInLog.query.filter(
            SignInLog.SISid == sis.SISid, SignInLog.isdelete == false()).order_by(SignInLog.createtime.desc()).all()
        signinlist = list()
        nosigninlist = list()
        for sil in sils:
            self._fill_user(sil, sil.USid)
            sil.add('createtime')
            sil.fill('SISstatus_zh', SigninLogStatus(sil.SISstatus).zh_value)
            sil.fill('SISstatus_eh', SigninLogStatus(sil.SISstatus).name)
            if sil.SISstatus == SigninLogStatus.wait.value:
                nosigninlist.append(sil)
            else:
                signinlist.append(sil)
        sis.fill('signinlist', signinlist)
        sis.fill('nosigninlist', nosigninlist)
        return Success(data=sis)

    @phone_required
    def signin(self):
        data = parameter_required(('plid', 'silnum'))
        user = get_current_user()
        sis = SignInSet.query.filter(SignInSet.PLid == data.get('plid'), SignInSet.isdelete == false()).order_by(
            SignInSet.createtime.desc()).first()
        with db.auto_commit():
            if not sis:
                raise StatusError('当前活动未开启签到')
            sil = SignInLog.query.filter(SignInLog.SISid == sis.SISid, SignInLog.USid == user.USid,
                                         SignInLog.isdelete == false()).first()

            if sil and sil.SISstatus == SigninLogStatus.success.value:
                raise StatusError('已签到')

            silnum = str(data.get('silnum'))
            if str(sis.SILnum) != silnum:
                raise ParamsError('签到码有误')

            sil.update({'SISstatus': SigninLogStatus.success.value})
            db.session.add(sil)

        return Success

    @phone_required
    def get_current_play(self):
        user = get_current_user()
        # now = datetime.now()
        # selfplay = Play.query.filter(Play.PLcreate == user.USid, Play.PLstatus == PlayStatus.activity.value).first()
        play = Play.query.join(EnterLog.PLid == Play.PLid).filter(
            Play.PLstatus == PlayStatus.activity.value,
            or_(Play.PLcreate == user.USid, EnterLog.USid == user.USid)).first()
        if not play:
            raise StatusError('当前无开启活动')
        self._fill_play(play)
        return Success(data=play)

    def _fill_user(self, model, usid):
        user = User.query.filter(User.USid == usid, User.isdelete == false()).first_('用户已失效')
        model.fill('USname', user.USname)
        model.fill('USlevel', '游客' if user.USlevel != self.guidelevel else '导游')
        model.fill('USheader', user.USheader)

    def _cancle_celery(self, conid):
        exist_task = conn.get(conid)
        if exist_task:
            exist_task = str(exist_task, encoding='utf-8')
            current_app.logger.info('已有任务id: {}'.format(exist_task))
            celery.AsyncResult(exist_task).revoke()

    def _update_cost_and_insurance(self, data, plid):
        instance_list = list()
        error_dict = {'costs': list(), 'insurances': list(), 'playrequires': list()}
        inid_list = list()
        cosid_list = list()
        costs_list = data.get('costs') or list()
        ins_list = data.get('insurances') or list()
        prs_list = data.get('playrequires') or list()
        for costid in costs_list:
            if isinstance(costid, dict):
                costid = costid.get('cosid')
            cost = Cost.query.filter_by(COSid=costid, isdelete=False).first()
            if not cost:
                error_dict.get('costs').append(costid)
                continue
            cost.update({"PLid": plid})
            cosid_list.append(costid)
            instance_list.append(cost)
        for inid in ins_list:
            if isinstance(inid, dict):
                inid = inid.get('inid')
            insurance = Insurance.query.filter_by(INid=inid, isdelete=False).first()
            if not insurance:
                error_dict.get('insurances').append(inid)
                continue
            insurance.update({"PLid": plid})
            inid_list.append(inid)
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
        # 删除不用的
        Cost.query.filter(
            Cost.COSid.notin_(cosid_list),
            Cost.PLid == plid,
            Cost.isdelete == false()
        ).delete_(synchronize_session=False)

        Insurance.query.filter(
            Insurance.INid.notin_(inid_list),
            Insurance.PLid == plid,
            Insurance.isdelete == false()
        ).delete_(synchronize_session=False)

        PlayRequire.query.filter(
            PlayRequire.PLid == plid,
            PlayRequire.PREid.notin_(preid_list),
            PlayRequire.isdelete == false()
        ).delete_(synchronize_session=False)
        db.session.add_all(instance_list)
        current_app.logger.info('本次更新出错的费用和保险以及需求项是 {}'.format(error_dict))

    def _update_plname(self, data):
        pllocation = data.get('pllocation')
        if isinstance(data.get('pllocation'), list):
            pllocation = self.connect_item.join(data.get('pllocation'))
        else:
            pllocation = self.connect_item.join(str(pllocation).split(self.split_item))

        try:
            plstart = data.get('plstarttime')
            plend = data.get('plendtime')
            if not isinstance(plstart, datetime):
                plstart = self._trans_time(plstart)
            current_app.logger.info('开始时间转换完成')
            if not isinstance(plend, datetime):
                plend = self._trans_time(plend)
            current_app.logger.info('结束时间转换完成')
        except:
            current_app.logger.error('转时间失败  开始时间 {}  结束时间 {}'.format(data.get('plstarttime'), data.get('plendtime')))
            raise ParamsError
        duration = plend - plstart
        if duration.days < 0:
            current_app.logger.error('起止时间有误')
            raise ParamsError
        days = to_chinese4(duration.days)
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
        # play.hide('PLcreate')
        play.fill('PLlocation', str(play.PLlocation).split(self.split_item))
        play.fill('PLproducts', str(play.PLproducts).split(self.split_item))
        play.fill('PLcontent', json.loads(play.PLcontent))
        play.fill('plstatus_zh', PlayStatus(play.PLstatus).zh_value)
        play.fill('plstatus_en', PlayStatus(play.PLstatus).name)
        playrequires = PlayRequire.query.filter_by(PLid=play.PLid, isdelete=False).order_by(
            PlayRequire.PREsort.asc()).all()

        play.fill('playrequires', [playrequire.PREname for playrequire in playrequires])
        enter_num = EnterLog.query.filter_by(PLid=play.PLid, isdelete=False).count()
        play.fill('enternum', enter_num)

        play.fill('editstatus', bool((not enter_num) and (play.PLstatus != PlayStatus.activity.value)))

        if common_user():
            user = get_current_user()
            el = EnterLog.query.filter(EnterLog.USid == user.USid, EnterLog.PLid == play.PLid,
                                       EnterLog.isdelete == false()).first()

            play.fill('joinstatus', bool(
                (play.PLcreate != user.USid) and (not el) and (int(enter_num) < int(play.PLnum)) and (
                        play.PLstatus == PlayStatus.publish.value)))
        else:
            play.fill('joinstatus',
                      bool((int(enter_num) < int(play.PLnum)) and (play.PLstatus == PlayStatus.publish.value)))

        user = User.query.filter_by(USid=play.PLcreate, isdelete=False).first()
        name = user.USname if user else '旗行平台'
        play.fill('PLcreate', name)

    def _fill_costs(self, play, show=True):
        costs_list = Cost.query.filter_by(PLid=play.PLid, isdelete=False).order_by(Cost.createtime.asc()).all()
        playsum = getattr(play, 'playsum', 0)
        costsum = sum([cost.COSsubtotal for cost in costs_list])
        playsum = Decimal(str(playsum)) + costsum
        if show:
            play.fill('costs', costs_list)
        play.fill('playsum', playsum)

    def _fill_insurances(self, play, show=True):
        ins_list = Insurance.query.filter_by(PLid=play.PLid, isdelete=False).order_by(Insurance.createtime.asc()).all()
        playsum = getattr(play, 'playsum', 0)
        inssum = sum([ins.INcost for ins in ins_list])
        playsum = Decimal(str(playsum)) + inssum
        if show:
            play.fill('insurances', ins_list)
        play.fill('playsum', playsum)

    def wechat_notify(self):
        data = self.wx_pay.to_dict(request.data)
        if not self.wx_pay.check(data):
            return self.wx_pay.reply(u"签名验证失败", False)
        out_trade_no = data.get('out_trade_no')
        current_app.logger.info("This is wechat_notify, opayno is {}".format(out_trade_no))
        # 修改当前用户参加状态
        with db.auto_commit():
            el = EnterLog.query.filter(EnterLog.ELpayNo == out_trade_no, EnterLog.isdelete == false()).first()
            if not el:
                current_app.logger.info('当前报名单不存在 {} '.format(out_trade_no))
                return self.wx_pay.reply("OK", True).decode()
            el.ELstatus = EnterLogStatus.success.value
            db.session.add(el)

        return self.wx_pay.reply("OK", True).decode()

    def _update_enter_cost(self, el, data):
        plid = data.get('plid')
        # costs = data.get('costs', [])
        costs = Cost.query.filter(Cost.PLid == plid, Cost.isdelete == false()).all()
        insurances = data.get('insurances', [])
        ecid = list()
        for cost in costs:
            # if isinstance(cost, dict):
            #     cost = cost.get('cosid')
            #
            # cost_model = Cost.query.filter(Cost.COSid == cost, Cost.isdelete == False, ).first_(
            #     '费用项已修改，请刷新重新选择')

            ecmodel = EnterCost.query.filter_by(
                ELid=el.ELid, ECcontent=cost.COSid, ECtype=EnterCostType.cost.value, isdelete=False).first()
            if not ecmodel:
                ecmodel = self._create_entercost(el.ELid, cost.COSid, EnterCostType.cost.value, cost.COSsubtotal)

            ecid.append(ecmodel.ECid)

        for insurance in insurances:
            if isinstance(insurance, dict):
                insurance = insurance.get('inid')
            ins_model = Insurance.query.filter_by(INid=insurance, isdelete=False).first_(
                '保险项有修改，请刷新重新选择')
            ecmodel = EnterCost.query.filter_by(
                ELid=el.ELid, ECcontent=ins_model.INid, ECtype=EnterCostType.insurance.value, isdelete=False).first()
            if not ecmodel:
                ecmodel = self._create_entercost(
                    el.ELid, ins_model.INid, EnterCostType.insurance.value, ins_model.INcost)
            ecid.append(ecmodel.ECid)
        # required_cost = Cost.query.filter(Cost.PLid == plid, Cost.isdelete == False)

        # 删除不用的
        EnterCost.query.filter(EnterCost.ECid.notin_(ecid), EnterCost.isdelete == False).delete_(
            synchronize_session=False)

    def _create_entercost(self, elid, eccontent, ectype, eccost):
        ecmodel = EnterCost.create({
            'ECid': str(uuid.uuid1()),
            'ELid': elid,
            'ECcontent': eccontent,
            'ECtype': ectype,
            'ECcost': eccost
        })
        db.session.add(ecmodel)
        return ecmodel

    def _check_plid(self, user, play):
        EnterLog.query.filter(
            EnterLog.ELstatus < EnterLogStatus.cancel.value,
            EnterLog.ELstatus > EnterLogStatus.error.value,
            EnterLog.PLid == play.PLid, EnterLog.USid == user.USid, EnterLog.isdelete == false()).delete_(
            synchronize_session=False)

        if play.PLstatus != PlayStatus.publish.value:
            raise StatusError('该活动已结束')
        if play.PLcreate == user.USid:
            raise ParamsError('报名的是自己创建的')
        # 查询同一时间是否有其他已参与活动
        user_enter = Play.query.join(EnterLog, Play.PLid == EnterLog.PLid).filter(
            or_(and_(Play.PLendTime < play.PLendTime, play.PLstartTime < Play.PLendTime),
                and_(Play.PLstartTime < play.PLendTime, play.PLstartTime < Play.PLstartTime)),
            or_(EnterLog.USid == user.USid), EnterLog.isdelete == false(), Play.isdelete == false(),
                                             Play.PLstatus < PlayStatus.close.value, Play.PLid != play.PLid).all()
        return bool(user_enter)

    def _update_elvalue(self, plid, data):
        preid_list = list()
        value_dict = dict()
        user_value = data.get('elvalue')
        for value in user_value:
            preid = value.get('preid')
            pr = PlayRequire.query.filter_by(PREid=preid, isdelete=False).first()
            if not pr:
                continue
            name = pr.PREname
            # value_dict.update(name=value.get('value'))
            value_dict[name] = value.get('value')
            preid_list.append(preid)
        play_require_list = PlayRequire.query.filter(
            PlayRequire.PREid.notin_(preid_list),
            PlayRequire.PLid == plid,
            PlayRequire.isdelete == false()).all()
        if play_require_list:
            prname = [pr.PREname for pr in play_require_list]
            raise ParamsError('缺失参数 {}'.format(prname))
        return value_dict
        # value_dict = json.dumps(data.get('elvalue'))
        # return value_dict

    def _trans_time(self, time_str):
        if re.match(r'^.*(:\d{2}){2}$', time_str):
            return_str = datetime.strptime(time_str, '%Y-%m-%d %H:%M:%S')
        else:
            return_str = datetime.strptime(time_str, '%Y-%m-%d %H:%M')
        return return_str

    def _random_num(self, numlen=4):
        return ''.join([random.randint(0, 9) for _ in range(numlen)])
