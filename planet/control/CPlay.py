import json
import random
import uuid
import re
from datetime import datetime, timedelta
from decimal import Decimal

from flask import current_app, request
from sqlalchemy import Date, or_, and_, false, extract

from planet.common.chinesenum import to_chinese4
from planet.common.error_response import ParamsError, StatusError, AuthorityError, ApiError
from planet.common.params_validates import parameter_required, validate_price
from planet.common.success_response import Success
from planet.common.token_handler import get_current_user, phone_required, common_user

from planet.config.enums import PlayStatus, EnterCostType, EnterLogStatus, PayType, Client, OrderFrom, SigninLogStatus, \
    CollectionType, CollectStatus, MiniUserGrade, ApplyStatus, MakeOverStatus, PlayPayType

from planet.common.Inforsend import SendSMS

from planet.config.http_config import API_HOST
from planet.config.secret import QXSignName, HelpTemplateCode

from planet.control.BaseControl import BaseController
from planet.extensions.register_ext import db, conn, mini_wx_pay

from planet.extensions.tasks import start_play, end_play, celery
from planet.extensions.weixin.pay import WeixinPayError
from planet.models import Cost, Insurance, Play, PlayRequire, EnterLog, EnterCost, User, Gather, SignInSet, SignInLog, \
    HelpRecord, UserCollectionLog, Notice, UserLocation, UserWallet, CancelApply, PlayDiscount, Agreement, MakeOver, \
    SuccessorSearchLog, PlayPay


class CPlay():

    def __init__(self):
        # super(CPlay, self).__init__()
        self.wx_pay = mini_wx_pay
        self.split_item = '!@##@!'
        self.realname = '真实姓名'
        self.conflict = '活动时间与您已创建或已参加的活动时间冲突，请重新确认'
        self.connect_item = '-'
        self.basecontrol = BaseController()
        self.guidelevel = 5

    """get 接口 """

    def get_current_location(self):
        args = request.args.to_dict()
        my_lat, my_long = args.get('latitude'), args.get('longitude')
        my_lat, my_long = self.check_lat_and_long(my_lat, my_long)
        # user = User.query.filter_by_(USid=getattr(request, 'user').id).first_('请重新登录')
        user = get_current_user()
        if my_lat and my_long and user:
            self.basecontrol.get_user_location(my_lat, my_long, user.USid)  # 记录位置

    def get_cost(self):
        data = parameter_required()
        plid = data.get('plid')
        if not plid:
            return Success(data=list())
        costs_list = Cost.query.filter_by(PLid=plid, isdelete=False).order_by(Cost.createtime.asc()).all()
        for cost in costs_list:
            cost.fill('COSdetail', json.loads(cost.COSdetail))

        return Success(data=costs_list)

    def get_insurance(self):
        data = parameter_required()
        plid = data.get('plid')
        if not plid:
            return Success(data=list())
        ins_list = Insurance.query.filter_by(PLid=plid, isdelete=False).order_by(Insurance.createtime.asc()).all()
        return Success(data=ins_list)

    def get_discount(self):
        data = parameter_required()
        plid = data.get('plid')
        if not plid:
            return Success(data=list())
        discounts = PlayDiscount.query.filter_by(PLid=plid, isdelete=False).order_by(PlayDiscount.PDtime.asc()).all()
        ag = Agreement.query.filter_by(AMtype=1, isdelete=False).first()

        role_words = json.loads(ag.AMcontent) if ag else ""
        pd_role_list = list()
        for pd in discounts:
            pd_role = '距离活动开始'
            if pd.PDdeltaDay:
                pd_role += '{}天'.format(pd.PDdeltaDay)
            if pd.PDdeltaHour:
                pd_role += '{}时'.format(pd.PDdeltaHour)
            pd_role += '前,扣款 {}'.format(pd.PDprice)
            pd_role_list.append(pd_role)

        role = "{} {}".format(role_words, ';'.join(pd_role_list))
        return Success(data={'discounts': discounts, 'role': role})

    @phone_required
    def get_play(self):
        data = parameter_required(('plid',))
        plid = data.get('plid')
        play = Play.query.filter_by(PLid=plid, isdelete=False).first_('活动已删除')
        self._fill_play(play)
        self._fill_costs(play)
        self._fill_insurances(play)
        self._fill_discount(play)
        return Success(data=play)

    @phone_required
    def get_play_list(self):
        data = parameter_required()
        user = get_current_user()
        join_or_create = int(data.get('playtype', 0))
        pltitle = data.get('pltitle')
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

            filter_args.add(
                and_(Play.PLstartTime.cast(Date) <= createtime, Play.PLendTime.cast(Date) >= createtime)
            )
        plstatus = data.get('plstatus')
        if (plstatus or plstatus == 0) and int(plstatus) >= 0:
            try:
                filter_args.add(Play.PLstatus == PlayStatus(int(data.get('plstatus'))).value)
            except:
                current_app.logger.info('状态筛选数据不对 状态{}'.format(data.get('plstatus')))
                raise ParamsError
        if pltitle:
            pltitle = re.escape(str(pltitle)).replace(r'_', r'\_')
            current_app.logger.info('get filter title =  {} '.format(pltitle))
            filter_args.add(Play.PLtitle.ilike('%{}%'.format(pltitle)))

        if join_or_create:
            filter_args.add(EnterLog.USid == user.USid)
            filter_args.add(EnterLog.PLid == Play.PLid)
            filter_args.add(EnterLog.isdelete == false())
        else:
            filter_args.add(or_(
                Play.PLcreate == user.USid,
                and_(MakeOver.PLid == Play.PLid, MakeOver.isdelete == false(), user.USid == MakeOver.MOsuccessor)))

        plays_list = Play.query.filter(*filter_args).order_by(
            Play.PLstartTime.desc()).all_with_page()
        for play in plays_list:
            self._fill_play(play, user)
            self._fill_costs(play, show=False)
            self._fill_insurances(play, show=False)
            self._fill_discount(play)
        return Success(data=plays_list)

    @phone_required
    def get_play_history(self):
        data = parameter_required()
        now = datetime.now()
        month = data.get('month') or now.month
        year = data.get('year') or now.year
        playstatus = int(data.get('publish', 0))

        user = get_current_user()
        filter_args = {
            or_(
                and_(
                    Play.PLid == EnterLog.PLid,
                    EnterLog.USid == user.USid,
                    EnterLog.isdelete == false()),
                Play.PLcreate == user.USid),
            Play.isdelete == false(),
            extract('month', Play.PLstartTime) == month,
            extract('year', Play.PLstartTime) == year,
        }
        if playstatus:
            filter_args.add(Play.PLstatus == PlayStatus.publish.value)
        else:
            filter_args.add(Play.PLstatus != PlayStatus.publish.value)
        play_list = Play.query.filter(*filter_args).order_by(Play.PLstartTime.desc()).all_with_page()
        for play in play_list:
            self._fill_play(play, user)
            self._fill_costs(play, show=False)
            self._fill_insurances(play, show=False)
            self._fill_discount(play)

        return Success(data=play_list)

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
            self._fill_discount(play)
        return Success(data=plays_list)

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
                if gather_point:
                    gather_location = self.init_location_dict(gather_point.GAlat,
                                                              gather_point.GAlon,
                                                              str(gather_point.GAtime)[11:16])

        res = {'gather_location': gather_location,
               'can_post': can_post, 'button_name': button_name}

        return Success(data=res)

    @phone_required
    def identity(self):
        """身份判断"""
        user = User.query.filter_by_(USid=getattr(request, 'user').id).first_('请重新登录')
        is_leader = self._is_tourism_leader(user.USid)
        return Success(data={'is_leader': bool(is_leader)})

    @phone_required
    def get_playrequire(self):
        data = parameter_required(('plid',))
        user = get_current_user()
        pre_list = PlayRequire.query.filter(PlayRequire.PLid == data.get('plid'), PlayRequire.isdelete == False) \
            .order_by(PlayRequire.PREsort.asc(), PlayRequire.createtime.desc()).all()
        for pre in pre_list:
            if pre.PREname == self.realname and user.USrealname:
                pre.fill('prevalue', user.USrealname)
        return Success(data=pre_list)

    @phone_required
    def get_enterlog(self):
        user = get_current_user()
        data = parameter_required(('plid',))
        plid = data.get('plid')
        el = EnterLog.query.filter(
            EnterLog.USid == user.USid, EnterLog.PLid == plid, EnterLog.isdelete == false()).first()
        play = Play.query.filter(Play.PLid == plid, Play.isdelete == false()).first_('活动已删除')
        ec_list = EnterCost.query.filter(EnterCost.ELid == el.ELid, EnterCost.isdelete == false()).all()

        self._fill_play(play, user)
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

    def get_notice(self):
        data = parameter_required(('plid',))
        plid = data.get('plid')
        play = Play.query.filter(Play.PLid == plid, Play.isdelete == false()).first_('活动已结束')
        notice = Notice.query.filter(Notice.PLid == play.PLid, Notice.isdelete == false()).first()
        if not notice:
            notice = Notice.create({
                'NOid': str(uuid.uuid1()),
                'PLid': plid,
                'NOcontent': json.dumps("")
            })
        notice.add('createtime')
        notice.fill('NOcontent', json.loads(notice.NOcontent))
        return Success(data=notice)

    @phone_required
    def get_member_location(self):
        data = parameter_required(('plid',))
        plid = data.get('plid')
        play = Play.query.filter(Play.PLid == plid, Play.isdelete == false()).first_('活动不存在')
        if play.PLstatus == PlayStatus.close.value:
            raise StatusError('活动结束，不再获取成员信息')

        els_list = EnterLog.query.filter(EnterLog.PLid == plid, EnterLog.ELstatus == EnterLogStatus.success.value,
                                         EnterLog.isdelete == false()).all()
        location_list = list()
        user = get_current_user()
        isleader = bool(play.PLcreate == user.USid)
        # todo 导游看到真实姓名
        leader = User.query.filter(User.USid == play.PLcreate, User.isdelete == false()).first()
        if not leader:
            raise ParamsError('活动数据有误')
        leader_location = UserLocation.query.filter(UserLocation.USid == leader.USid,
                                                    UserLocation.isdelete == false()).order_by(
            UserLocation.createtime.desc()).first()
        self._fill_location(leader_location, isleader=True, realname=True)

        location_list.append(leader_location)
        for el in els_list:
            location = UserLocation.query.filter(UserLocation.USid == el.USid,
                                                 UserLocation.isdelete == false()).order_by(
                UserLocation.createtime.desc()).first()
            if not location:
                continue
            self._fill_location(location, realname=isleader)
            location_list.append(location)
        return Success(data=location_list)

    @phone_required
    def get_current_play(self):
        user = get_current_user()

        play = Play.query.join(EnterLog, EnterLog.PLid == Play.PLid).filter(
            Play.PLstatus == PlayStatus.activity.value,
            or_(Play.PLcreate == user.USid, EnterLog.USid == user.USid)).first()
        if not play:
            raise StatusError('当前无开启活动')
        self._fill_play(play, user)
        return Success(data=play)

    @phone_required
    def get_enter_user(self):
        data = parameter_required(('plid',))
        plid = data.get('plid')
        play = Play.query.filter(Play.isdelete == false(), Play.PLid == plid).first_('活动已删除')
        user = get_current_user()
        els = EnterLog.query.join(User, User.USid == EnterLog.USid).filter(EnterLog.PLid == play.PLid,
                                                                           EnterLog.USid != user.USid,
                                                                           User.isdelete == false(),
                                                                           EnterLog.ELstatus == EnterLogStatus.success.value,
                                                                           EnterLog.isdelete == false()).order_by(
            EnterLog.createtime.desc()).all_with_page()

        user_list = list()
        for el in els:
            usid = el.USid
            self._fill_user(el, usid)

            ucl = UserCollectionLog.query.filter(UserCollectionLog.UCLcoType == CollectionType.user.value,
                                                 UserCollectionLog.isdelete == False)
            followed = ucl.filter(UserCollectionLog.UCLcollector == user.USid,
                                  UserCollectionLog.UCLcollection == usid).first()
            be_followed = ucl.filter(UserCollectionLog.UCLcollector == usid,
                                     UserCollectionLog.UCLcollection == user.USid).first()
            follow_status = CollectStatus.none.value if not followed \
                else CollectStatus.aandb.value if be_followed else CollectStatus.atob.value
            el.fill('follow_status', follow_status)
            el.fill('follow_status_en', CollectStatus(follow_status).name)
            el.fill('follow_status_zh', CollectStatus(follow_status).zh_value)
            user_list.append(el)
        return Success(data=user_list)

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
            self._fill_user(sil, sil.USid, '用户已失效')
            sil.add('updatetime')
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
    def get_mosuccessor(self):
        data = parameter_required({'usrealname': '真实姓名', 'ustelphone': '手机号', 'usidentification': '身份证', })
        user = get_current_user()
        mosuccessor = User.query.filter_by(UStelphone=data.get('ustelphone')).first()

        with db.auto_commit():
            ssl = SuccessorSearchLog.create({
                'SSLid': str(uuid.uuid1()),
                'MOassignor': user.USid,
                'MOsuccessor': mosuccessor.USid if mosuccessor else None,
                'USrealname': data.get('usrealname'),
                'UStelphone': data.get('ustelphone'),
                'USidentification': data.get('usidentification'),
            })
            db.session.add(ssl)
        if not mosuccessor:
            raise ParamsError('查无此人')
        return Success(data=mosuccessor.USid)

    @phone_required
    def get_undertake_agreement(self):
        data = parameter_required(('plid',))
        play = Play.query.filter_by(PLid=data.get('plid'), isdelete=False).first_('活动已删除')
        makeover = MakeOver.query.filter_by(PLid=play.PLid, MOstatus=MakeOverStatus.success.value).first_('活动单未完成')
        assignor = User.query.filter_by(USid=makeover.MOassignor, isdelete=False).first_('转让人不存在')
        successor = User.query.filter_by(USid=makeover.MOsuccessor, isdelete=False).first_('承接人不存在')

        agreement = Agreement.query.filter_by(AMtype=0, isdelete=False).order_by(Agreement.updatetime.desc()).first()
        content = agreement.AMcontent
        current_app.logger.info('get content before add = {}'.format(content))
        re_c = content.format(assignor.USname, play.PLname, play.PLstartTime, play.PLendTime, successor.USname,
                              successor.UStelphone, makeover.MOprice, successor.USname, successor.USname,
                              makeover.updatetime)
        current_app.logger.info('get content = {}'.format(re_c))
        return Success(data=re_c)

    @phone_required
    def get_make_over(self):
        data = parameter_required(('moid',))
        user = get_current_user()
        mo = MakeOver.query.filter_by(MOid=data.get('moid'), isdelete=False).first()
        play = Play.query.filter_by(PLid=mo.PLid, isdelete=False).first()
        self._fill_play(play, user)
        self._fill_mo(play, mo, detail=True)

        return Success(data=mo)

    @phone_required
    def get_make_over_list(self):
        data = parameter_required(('motype',))
        user = get_current_user()
        date = data.get('date')
        if date and not re.match(r'^20\d{2}-\d{2}$', str(date)):
            raise ParamsError('date 格式错误')
        year, month = str(date).split('-') if date else (datetime.now().year, datetime.now().month)
        filter_args = {
            Play.PLid == MakeOver.PLid,
            Play.isdelete == false(),

            extract('month', MakeOver.createtime) == month,
            extract('year', MakeOver.createtime) == year,
            MakeOver.isdelete == false()
        }
        if int(data.get('motype')):
            # 转入
            filter_args.add(MakeOver.MOsuccessor == user.USid)
        else:
            # 转出
            filter_args.add(MakeOver.MOassignor == user.USid)
        mo_list = MakeOver.query.filter(*filter_args).order_by(MakeOver.createtime.desc()).all_with_page()
        for mo in mo_list:
            play = Play.query.filter_by(PLid=mo.PLid, isdelete=False).first()
            self._fill_mo(play, mo)
        return Success(data=mo_list)

    """post 接口"""

    def wechat_notify(self):
        """微信支付回调接口"""
        data = self.wx_pay.to_dict(request.data)
        if not self.wx_pay.check(data):
            return self.wx_pay.reply(u"签名验证失败", False)
        out_trade_no = data.get('out_trade_no')
        current_app.logger.info("This is wechat_notify, opayno is {}".format(out_trade_no))

        with db.auto_commit():
            pp = PlayPay.query.filter_by(PPpayno=out_trade_no, isdelete=False).first()

            if not pp:
                # 支付流水不存在 钱放在平台
                return self.wx_pay.reply("OK", True).decode()
            pp.update({
                'PPpaytime': data.get('time_end'),
                'PPpaysn': data.get('transaction_id'),
                'PPpayJson': json.dumps(data)
            })
            db.session.add(pp)
            if pp.PPpayType == PlayPayType.enterlog.value:
                self._enter_log(pp)
            elif pp.PPpayType == PlayPayType.undertake.value:
                current_app.logger.info('开始修改转让单')
                self._undertake(pp)
            else:
                current_app.logger.info('获取到异常数据 {}'.format(pp.__dict__))
                return self.wx_pay.reply("OK", True).decode()
        return self.wx_pay.reply("OK", True).decode()

    @phone_required
    def set_play(self):
        data = parameter_required()
        plid = data.get('plid')

        with db.auto_commit():
            user = get_current_user()
            usid = user.USid
            if plid:
                play = Play.query.filter_by(PLid=plid, isdelete=False).first()
                if play:
                    # raise ParamsError('')
                    if play.PLstatus == PlayStatus.activity.value:
                        raise StatusError('进行中活动无法修改')

                    if user.USid != play.PLcreate:
                        raise AuthorityError('只能修改自己的活动')

                    if self._check_user_play(user, play):
                        raise StatusError(self.conflict)

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
                    'plstarttime': update_dict.get('PLstartTime') or play.PLstartTime,
                    'plendtime': update_dict.get('PLendTime') or play.PLendTime,
                }

                plname = self._update_plname(playname)
                update_dict.update(PLname=plname)
                play.update(update_dict)
                db.session.add(play)
                self._update_cost_and_insurance(data, play)
                self._auto_playstatus(play)
                return Success('更新成功', data=plid)

            data = parameter_required(
                {'plimg': '活动封面', 'plstarttime': '开始时间', 'plendtime': '结束时间', 'pllocation': '活动地点',
                 'plnum': '团队最大承载人数', 'pltitle': '行程推文标题', 'plcontent': '活动详情'})

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
                'PLcreate': usid,
                'PLstatus': PlayStatus(int(data.get('plstatus', 0))).value,
                'PLname': plname,
                'PLproducts': self.split_item.join(data.get('plproducts', [])),
            })
            if self._check_user_play(user, play):
                raise StatusError(self.conflict)
            db.session.add(play)
            self._update_cost_and_insurance(data, play)

            self._auto_playstatus(play)
        return Success(data=plid)

    @phone_required
    def set_cost(self):
        data = parameter_required()
        with db.auto_commit():
            costs = data.get('costs', list())
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

                subtotal = validate_price(str(cost.get('cossubtotal') or 0))
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

    @phone_required
    def set_discount(self):
        data = parameter_required()
        with db.auto_commit():
            discounts = data.get('discounts') or list()
            instance_list = list()
            pdid_list = list()
            for pd in discounts:
                current_app.logger.info('get cost {}'.format(pd))
                pdid = pd.get('pdid')
                if pd.get('delete'):
                    pd_instance = PlayDiscount.query.filter_by(PDid=pdid, isdelete=False).first()
                    if not pd_instance:
                        continue
                    if self._check_activity_play(pd_instance):
                        raise StatusError('进行中活动无法修改')
                    # return Success('删除成功')
                    pd_instance.isdelete = True
                    instance_list.append(pd_instance)
                    current_app.logger.info('删除退团费用 {}'.format(pdid))
                    continue

                pdprice = validate_price(str(pd.get('pdprice') or 0))
                if pdid:
                    pd_instance = PlayDiscount.query.filter_by(PDid=pdid, isdelete=False).first()
                    if pd_instance:
                        if self._check_activity_play(pd_instance):
                            raise StatusError('进行中活动无法修改')
                        update_dict = self._get_update_dict(pd_instance, pd)
                        if update_dict.get('PDprice'):
                            update_dict.update(PDprice=pdprice)

                        pd_instance.update(update_dict)
                        instance_list.append(pd_instance)
                        pdid_list.append(pdid)
                        continue
                pdid = str(uuid.uuid1())
                if not pd.get('pddeltaday') and not pd.get('pddeltahour'):
                    raise ParamsError('时间差值不能为空')

                pd_instance = PlayDiscount.create({
                    "PDid": pdid,
                    "PDdeltaDay": pd.get('pddeltaday'),
                    "PDdeltaHour": pd.get('pddeltahour'),
                    "PDprice": pdprice,
                })
                instance_list.append(pd_instance)
                pdid_list.append(pdid)
            db.session.add_all(instance_list)

        return Success(data=pdid_list)

    @phone_required
    def set_insurance(self):
        data = parameter_required()
        with db.auto_commit():
            insurance_list = data.get('insurance') or list()
            instance_list = list()
            inid_list = list()
            for ins in insurance_list:
                current_app.logger.info('get Insurance {} '.format(ins))
                inid = ins.get('inid')
                incost = validate_price(str(ins.get('incost') or 0))

                current_app.logger.info(' changed insurance cost = {}'.format(incost))
                if ins.get('delete'):
                    current_app.logger.info('删除 Insurance {} '.format(inid))
                    ins_instance = Insurance.query.filter_by(INid=inid, isdelete=False).first()
                    if not ins_instance:
                        continue
                    if self._check_activity_play(ins_instance):
                        raise StatusError('进行中活动无法修改')
                    ins_instance.isdelete = True
                    continue

                if inid:
                    ins_instance = Insurance.query.filter_by(INid=inid, isdelete=False).first()
                    if ins_instance:
                        if self._check_activity_play(ins_instance):
                            raise StatusError('进行中活动无法修改')
                        update_dict = self._get_update_dict(ins_instance, ins)
                        if update_dict.get('INcost'):
                            update_dict.update(INcost=incost)
                        ins_instance.update(update_dict)
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

    @phone_required
    def help(self):
        """一键求救"""
        user = User.query.filter_by_(USid=getattr(request, 'user').id).first_('请重新登录')
        data = request.json
        latitude, longitude = data.get('latitude'), data.get('longitude')
        latitude, longitude = self.check_lat_and_long(latitude, longitude)
        self.basecontrol.get_user_location(latitude, longitude, user.USid)
        my_created_play = self._is_tourism_leader(user.USid)  # 是否领队
        phone_list, helper_list, plid = [], [], None
        if my_created_play:
            plid = my_created_play.PLid
            usphones = db.session.query(User.UStelphone, User.USname).join(EnterLog, EnterLog.USid == User.USid).filter(
                EnterLog.isdelete == false(),
                EnterLog.PLid == my_created_play.PLid,
                EnterLog.ELstatus == EnterLogStatus.success.value,
                User.isdelete == false()
            ).all()
            phone_list = list(map(lambda x: x[0], usphones))
            helper_list = list(map(lambda x: x[1], usphones))
            current_app.logger.info('领队正在求救')
        else:
            my_joined_play = self._ongoing_play_joined(user.USid)
            if my_joined_play:
                plid = my_joined_play.PLid
                phone = db.session.query(User.UStelphone, User.USname).filter(
                    User.isdelete == false(),
                    User.USid == my_joined_play.PLcreate).first()
                phone_list.append(phone[0])
                helper_list.append(phone[1])
                current_app.logger.info('团员正在求救')
        if not phone_list:
            raise StatusError('当前没有参加活动')
        # 发送求救短信
        for index, usphone in enumerate(phone_list):
            params = {"name": helper_list[index], "name2": user.USname, "telphone": user.UStelphone}
            # todo 签名未审核通过，上线前替换 sign_name=QXSignName
            response_send_message = SendSMS(usphone, params, templatecode=HelpTemplateCode)
            if response_send_message:
                current_app.logger.info('send help sms param: {}'.format(params))
        # 求救记录
        with db.auto_commit():
            help_record = HelpRecord.create({'HRid': str(uuid.uuid1()),
                                             'USid': user.USid,
                                             'UStelphone': user.UStelphone,
                                             'USlatitude': latitude,
                                             'USlongitude': longitude,
                                             'PLid': plid,
                                             'HRphones': json.dumps(phone_list)})
            db.session.add(help_record)

        return Success(data={'phone': phone_list})

    @phone_required
    def set_gather(self):
        """发起集合点"""
        data = parameter_required({'latitude': '维度', 'longitude': '经度', 'time': '时间'})
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
        my_created_play = self._is_tourism_leader(user.USid)
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

    @phone_required
    def join(self):
        data = parameter_required(('plid',))
        plid = data.get('plid')
        elid = data.get('elid')
        repay = data.get('repay')
        opayno = self._opayno()
        play = Play.query.filter_by(PLid=plid, isdelete=False).first_('活动已删除')
        user = get_current_user()

        with db.auto_commit():
            # current_app.logger.info('plid {}'.format(play.PLid))
            if self._check_plid(user, play):
                raise StatusError(self.conflict)
            # 优先检测是否继续支付
            if repay:
                el = EnterLog.query.filter_by(PLid=plid, isdelete=False).first_('报名记录已删除')
                if el.ELstatus != EnterLogStatus.wait_pay.value:
                    raise StatusError('当前报名记录已支付或者已删除')
                elid = el.ELid
            else:
                if elid:
                    el = EnterLog.query.filter_by(ELid=elid, isdelete=False).first()
                    if el:
                        # 校验修改
                        if el.PLid != plid:
                            raise ParamsError(self.conflict)
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

                # change_name = False
                if elvalue.get('realname'):
                    if user.USrealname and user.USrealname != elvalue.get(self.realname):
                        raise ParamsError('真实姓名与已认证姓名不同')

                    elif user.USplayName != elvalue.get(self.realname):
                        user.USplayName = elvalue.get(self.realname)
                        db.session.add(user)

        body = play.PLname[:16] + '...'
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

        pay_args = self._add_pay_detail(opayno=opayno,
                                        body=body, PPpayMount=mount_price, openid=openid, PPcontent=el.ELid,
                                        PPpayType=PlayPayType.enterlog.value)

        response = {
            'pay_type': PayType.wechat_pay.name,
            'opaytype': PayType.wechat_pay.value,
            'elid': elid,
            'args': pay_args
        }
        return Success(data=response)

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

    @phone_required
    def signin(self):
        data = parameter_required()

        plid, silnum = data.get('plid'), data.get('silnum')
        # 参数校验
        if not plid:
            raise ParamsError('当前没有开启中的活动')
        if not silnum:
            raise ParamsError('签到码不能为空')

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
    def create_notice(self):
        data = parameter_required({'plid': '', 'nocontent': '公告内容'})
        user = get_current_user()
        plid = data.get('plid')
        nocontent = data.get('nocontent')
        with db.auto_commit():
            play = Play.query.filter(Play.PLid == plid, Play.PLcreate == user.USid, Play.isdelete == false()).first_(
                '只能修改自己的活动公告')
            if play.PLstatus == PlayStatus.close.value:
                raise StatusError('活动结束不能再发公告')

            # 删除原有的公告
            Notice.query.filter(Notice.PLid == plid, Notice.isdelete == false()).delete_(synchronize_session=False)

            notice = Notice.create({
                'NOid': str(uuid.uuid1()),
                'PLid': plid,
                'NOcontent': json.dumps(nocontent)
            })
            db.session.add(notice)

        return Success(data=notice.NOid)

    def cancel(self):
        """用户取消"""
        data = parameter_required(('plid',))
        plid = data.get('plid')

        with db.auto_commit():
            user = get_current_user()
            play = Play.query.filter(Play.PLid == plid, Play.PLstatus < PlayStatus.activity.value,
                                     Play.isdelete == false()).first_('活动已开始或已结束')
            el = EnterLog.query.filter(EnterLog.PLid == plid, EnterLog.USid == user.USid,
                                       EnterLog.isdelete == false()).first_('报名记录未生效')
            elid = el.ELid

            cap = CancelApply.query.filter(
                CancelApply.ELid == elid,
                CancelApply.isdelete == false(),
                CancelApply.CAPstatus >= ApplyStatus.wait_check.value).first()
            if cap:
                raise StatusError('已经提交申请，请等待')
            # capreason = str(data.get('capreason')).replace(' ', '').replace('\n', '').replace('\t', '')
            CancelApply.query.filter(CancelApply.ELid == elid, CancelApply.isdelete == false()).delete_(
                synchronize_session=False)
            cap = CancelApply.create({
                'CAPid': str(uuid.uuid1()),
                'ELid': elid,
                'CAPstatus': ApplyStatus.wait_check.value,
            })
            db.session.add(cap)
            # 如果还没有付款成功则不退钱
            if el.ELstatus < EnterLogStatus.success.value:
                el.ELstatus = EnterLogStatus.cancel.value
                return Success()
            # 退款
            now = datetime.now()
            discounts = PlayDiscount.query.filter_by(PLid=plid, isdelete=False).order_by(
                PlayDiscount.PDtime.asc()).all()

            mount_price = sum(
                [ec.ECcost for ec in
                 EnterCost.query.filter(EnterCost.ELid == elid, EnterCost.isdelete == false()).all()])
            # return_price = Decimal(str(mount_price)) - discount
            discount = mount_price
            for pd in discounts:
                if now < pd.PDtime:
                    continue
                discount = Decimal(str(pd.PDprice))
                break
            return_price = discount

            el.ELstatus = EnterLogStatus.refund.value
            # 扣除领队钱
            leader = User.query.filter_by(USid=play.PLcreate, isdelete=False).first()
            uw = UserWallet.query.filter_by(USid=leader.USid, isdelete=False).first()
            if uw.UWcash < return_price:
                current_app.logger.error('领队账户钱不够')
                raise ParamsError('退款失败，请直接联系领队 电话 {}'.format(leader.UStelphone))
            uw.UWcash = Decimal(str(uw.UWcash)) - return_price
            uw.UWbalance = Decimal(str(uw.UWbalance)) - return_price
            uw.UWtotal = Decimal(str(uw.UWtotal)) - return_price
            current_app.logger.info('return_price = {} mount_price={}'.format(return_price, mount_price))
            if API_HOST != 'https://www.bigxingxing.com':
                return_price = 0.01
                mount_price = 0.01

            self._refund_to_user(
                out_trade_no=el.ELpayNo,
                out_request_no=cap.CAPid,
                mount=return_price,
                old_total_fee=mount_price
            )
        return Success()

    @phone_required
    def make_over(self):
        data = parameter_required({'plid': '', 'moprice': '转让价格', 'usrealname': '真实姓名',
                                   'ustelphone': '手机号', 'usidentification': '身份证'})
        with db.auto_commit():
            user = get_current_user()
            mosuccessor = User.query.filter_by(UStelphone=data.get('ustelphone'), isdelete=False).first()

            ssl = SuccessorSearchLog.create({
                'SSLid': str(uuid.uuid1()),
                'MOassignor': user.USid,
                'MOsuccessor': mosuccessor.USid if mosuccessor else None,
                'USrealname': data.get('usrealname'),
                'UStelphone': data.get('ustelphone'),
                'USidentification': data.get('usidentification'),
            })

            db.session.add(ssl)
            if not mosuccessor:
                raise ParamsError('查无此人')

            # 活动校验
            play = Play.query.filter_by(PLid=data.get('plid'), isdelete=False).first_('活动不存在')
            if play.PLstatus >= PlayStatus.activity.value:
                raise StatusError('活动已开始')
            user = get_current_user()
            # 价格校验
            moprice = validate_price(str(data.get('moprice') or 0))

            # 添加记录
            makeover = MakeOver.create({
                "MOid": str(uuid.uuid1()),
                'PLid': play.PLid,
                'MOassignor': user.USid,
                'MOsuccessor': mosuccessor.USid,
                'MOstatus': MakeOverStatus.wait_confirm.value,
                'MOprice': moprice
            })
            db.session.add(makeover)
            # 修改状态
            play.PLstatus = PlayStatus.makeover.value
            db.session.add(play)

        return Success(data=makeover.MOid)

    @phone_required
    def undertake(self):
        data = parameter_required(('plid', 'mostatus'))
        with db.auto_commit():
            plid = data.get('plid')
            play = Play.query.filter_by(PLid=plid, isdelete=False).first_('活动已删除')
            user = get_current_user()
            if self._check_user_play(user, play):
                raise StatusError(self.conflict)
            makeover = MakeOver.query.filter_by(PLid=plid, isdelete=False).first_('转让记录已失效')
            if play.PLstatus < PlayStatus.makeover.value:
                makeover.isdelete = True
                return StatusError('转让已取消')

            if makeover.MOsuccessor != user.USid:
                raise AuthorityError('无权限')
            # if makeover.MOstatus ==
            mostatus = int(data.get('mostatus'))
            if mostatus:
                makeover.MOstatus = MakeOverStatus.wait_pay.value
                play.PLstatus = PlayStatus.wait_pay.value
            else:
                # todo 拒绝之后无操作
                makeover.MOstatus = MakeOverStatus.refuse.value
                play.PLstatus = PlayStatus.publish.value

            db.session.add(makeover)
            db.session.add(play)
        return Success(data=makeover.MOid)

    @phone_required
    def payment(self):
        data = parameter_required()
        plid = data.get('plid')
        moid = data.get('moid')
        opayno = self._opayno()
        with db.auto_commit():
            user = get_current_user()
            if moid:
                makeover = MakeOver.query.filter_by(MOid=moid, isdelete=False).first_('转让记录已失效')
                play = Play.query.filter_by(PLid=makeover.PLid, isdelete=False).first_('活动已删除')

            elif plid:
                play = Play.query.filter_by(PLid=plid, isdelete=False).first_('活动已删除')

                makeover = MakeOver.query.filter(
                    MakeOver.PLid == plid,
                    MakeOver.isdelete == false()).first_('转让单已失效')
            else:
                raise ParamsError('活动或转让单参数缺失')
            # 转让单状态
            if makeover.MOstatus != MakeOverStatus.wait_pay.value:
                if makeover.MOstatus == MakeOverStatus.wait_confirm.value:
                    current_app.logger.info('用户 {} 直接 支付 {} 转让单'.format(user.USname, makeover.MOid))
                else:
                    raise StatusError('当前转让单已{}，请勿支付'.format(MakeOverStatus(makeover.MOstatus).zh_value))
            if makeover.MOsuccessor != user.USid:
                raise AuthorityError('当前活动不能承接支付')
            # 活动单状态
            if play.PLstatus < PlayStatus.makeover.value:
                makeover.isdelete = False
                db.session.add(makeover)
                return StatusError('活动转让已取消')
            makeover.MOpayNo = opayno
            db.session.add(makeover)

        # 支付
        openid = user.USopenid1
        pay_args = self._add_pay_detail(**{
            'body': '转让{}...'.format(play.PLname[:10]),
            'PPpayMount': makeover.MOprice,
            'openid': openid,
            'opayno': opayno,
            'PPpayType': PlayPayType.undertake.value,
            'PPcontent': makeover.MOid})

        response = {
            'pay_type': PayType.wechat_pay.name,
            'opaytype': PayType.wechat_pay.value,
            'moid': moid,
            'args': pay_args
        }
        return Success(data=response)

    """内部方法"""

    def _fill_user(self, model, usid, error_msg=None, realname=False):
        """填充活动用户信息"""
        if error_msg:
            user = User.query.filter(User.USid == usid, User.isdelete == false()).first_(error_msg)
        else:
            user = User.query.filter(User.USid == usid, User.isdelete == false()).first()
            if not user:
                return False
        usname = user.USname
        if realname:
            if user.USrealname:
                usname = user.USrealname
            elif user.USplayName:
                usname = user.USplayName
            model.fill('UStelphone', user.UStelphone)

        model.fill('USname', usname)
        uslevel = MiniUserGrade(user.USminiLevel or 0)
        model.fill('USminiLevel', uslevel.value)
        model.fill('USminiLevel_zh', uslevel.zh_value)
        model.fill('USheader', user['USheader'])

        return True

    def _cancle_celery(self, conid):
        exist_task = conn.get(conid)
        if exist_task:
            exist_task = str(exist_task, encoding='utf-8')
            current_app.logger.info('已有任务id: {}'.format(exist_task))
            celery.AsyncResult(exist_task).revoke()
            conn.delete(conid)

    def _update_cost_and_insurance(self, data, play):
        """更新活动费用和保险"""
        """更新退团折扣"""
        plid = play.PLid
        instance_list = list()
        error_dict = {'costs': list(), 'insurances': list(), 'playrequires': list(), 'playdiscount': list()}
        inid_list = list()
        cosid_list = list()
        playdiscount = list()
        costs_list = data.get('costs') or list()
        ins_list = data.get('insurances') or list()
        prs_list = data.get('playrequires') or list()
        pds_list = data.get('discounts') or list()
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

        for pdid in pds_list:
            if isinstance(pdid, dict):
                pdid = pdid.get('pdid')
            pdinstance = PlayDiscount.query.filter_by(PDid=pdid, isdelete=False).first()
            if not pdinstance:
                error_dict.get('playdiscount').append(pdid)
                continue
            play_time = play.PLstartTime
            if isinstance(play_time, str):
                play_time = self._trans_time(play_time)
            pdtimedelta = timedelta(days=(pdinstance.PDdeltaDay or 0), hours=(pdinstance.PDdeltaHour or 0))
            pdinstance.update({"PLid": plid, 'PDtime': play_time - pdtimedelta})
            playdiscount.append(pdid)
            instance_list.append(pdinstance)
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
        PlayDiscount.query.filter(
            PlayDiscount.PLid == plid,
            PlayDiscount.PDid.notin_(pds_list),
            PlayDiscount.isdelete == false()
        ).delete_(synchronize_session=False)
        db.session.add_all(instance_list)
        current_app.logger.info('本次更新出错的费用和保险以及需求项是 {}'.format(error_dict))

    def _update_plname(self, data):
        """更新活动名称 同时校验时间"""
        pllocation = data.get('pllocation')
        if isinstance(data.get('pllocation'), list):
            pllocation = self.connect_item.join(data.get('pllocation'))
        else:
            pllocation = self.connect_item.join(str(pllocation).split(self.split_item))

        try:
            now = datetime.now()
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

        if now > plstart:
            current_app.logger.info('now is {} plstart is {}'.format(now, plstart))
            raise ParamsError('开始时间不能小于当前时间')

        duration = plend - plstart
        if duration.days < 0:
            current_app.logger.error('起止时间有误')
            raise ParamsError
        # 修改数据格式
        data['plstarttime'] = plstart
        data['plendtime'] = plend

        days = to_chinese4(duration.days + 1)
        plname = '{}·{}日'.format(pllocation, days)
        return plname

    def _check_activity_play(self, check_model):
        """校验活动是否合法"""
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

    def _fill_play(self, play, user=None):
        play.fill('PLlocation', str(play.PLlocation).split(self.split_item))
        play.fill('PLproducts', str(play.PLproducts).split(self.split_item))
        play.fill('PLcontent', json.loads(play.PLcontent))
        play.fill('plstatus_zh', PlayStatus(play.PLstatus).zh_value)
        play.fill('plstatus_en', PlayStatus(play.PLstatus).name)
        playrequires = PlayRequire.query.filter_by(PLid=play.PLid, isdelete=False).order_by(
            PlayRequire.PREsort.asc()).all()

        play.fill('playrequires', [playrequire.PREname for playrequire in playrequires])
        enter_num = EnterLog.query.filter_by(PLid=play.PLid, ELstatus=EnterLogStatus.success.value,
                                             isdelete=False).count()
        play.fill('enternum', enter_num)
        if common_user():
            user = user or get_current_user()
            play.fill('editstatus', bool(
                ((not enter_num and play.PLstatus == PlayStatus.publish.value) or
                 (play.PLstatus in [PlayStatus.draft.value, PlayStatus.close.value])) and
                (play.PLcreate == user.USid)))

            play.fill('playtype', bool(play.PLcreate != user.USid))
            el = EnterLog.query.filter(EnterLog.USid == user.USid, EnterLog.PLid == play.PLid,
                                       EnterLog.isdelete == false()).first()
            play.fill('repaystatus', bool(
                (play.PLcreate != user.USid) and
                (el and el.ELstatus == EnterLogStatus.wait_pay.value) and
                (int(enter_num) < int(play.PLnum)) and
                (play.PLstatus == PlayStatus.publish.value)))

            play.fill('joinstatus', bool(
                (play.PLcreate != user.USid) and
                (not el or el.ELstatus == EnterLogStatus.wait_pay.value) and
                (int(enter_num) < int(play.PLnum)) and
                (play.PLstatus == PlayStatus.publish.value)))

            isrefund = True
            if el:
                cap = CancelApply.query.filter_by(ELid=el.ELid).first()
                if cap:
                    isrefund = False
            play.fill('isrefund', isrefund)
        else:
            play.fill('editstatus', False)
            play.fill('joinstatus',
                      bool((int(enter_num) < int(play.PLnum)) and (play.PLstatus == PlayStatus.publish.value)))

        leader = User.query.filter_by(USid=play.PLcreate, isdelete=False).first()

        name = leader.USname if leader else '旗行平台'
        play.fill('PLcreate', name)

        self._fill_make_over(play)

    def _fill_costs(self, play, show=True):
        costs_list = Cost.query.filter_by(PLid=play.PLid, isdelete=False).order_by(Cost.createtime.asc()).all()
        playsum = getattr(play, 'playsum', 0)
        costsum = sum([cost.COSsubtotal for cost in costs_list])
        playsum = Decimal(str(playsum)) + costsum
        if show:
            play.fill('costs', [cost.COSid for cost in costs_list])
        play.fill('playsum', playsum)

    def _fill_insurances(self, play, show=True):
        ins_list = Insurance.query.filter_by(PLid=play.PLid, isdelete=False).order_by(Insurance.createtime.asc()).all()
        playsum = getattr(play, 'playsum', 0)
        inssum = sum([ins.INcost for ins in ins_list])
        playsum = Decimal(str(playsum)) + inssum
        if show:
            play.fill('insurances', [ins.INid for ins in ins_list])
        play.fill('playsum', playsum)

    def _fill_discount(self, play):
        discounts = PlayDiscount.query.filter_by(PLid=play.PLid, isdelete=False).order_by(
            PlayDiscount.PDtime.asc()).all()
        play.fill('discounts', [discount.PDid for discount in discounts])

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
        # EnterLog.query.filter(
        #     EnterLog.ELstatus < EnterLogStatus.cancel.value,
        #     EnterLog.ELstatus > EnterLogStatus.error.value,
        #     EnterLog.PLid == play.PLid, EnterLog.USid == user.USid, EnterLog.isdelete == false()).delete_(
        #     synchronize_session=False)

        if play.PLstatus != PlayStatus.publish.value:
            raise StatusError('该活动已结束')
        if play.PLcreate == user.USid:
            raise ParamsError('报名的是自己创建的')

        return bool(self._check_user_play(user, play))

    def _check_user_play(self, user, play):
        # 查询同一时间是否有其他已参与活动
        return Play.query.filter(
            or_(and_(Play.PLendTime <= play.PLendTime, play.PLstartTime <= Play.PLendTime),
                and_(Play.PLstartTime <= play.PLendTime, play.PLstartTime <= Play.PLstartTime)),
            or_(and_(EnterLog.USid == user.USid,
                     EnterLog.PLid == Play.PLid,
                     EnterLog.ELstatus == EnterLogStatus.success.value,
                     EnterLog.isdelete == false()),
                Play.PLcreate == user.USid),
            Play.isdelete == false(),
            Play.PLstatus < PlayStatus.close.value, Play.PLid != play.PLid).all()

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
            if name == self.realname:
                value_dict.update(realname=True)
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
        return ''.join([str(random.randint(0, 9)) for _ in range(numlen)])

    def _fill_location(self, location, isleader=False, realname=False):
        location.fields = ['createtime']
        self._fill_user(location, location.USid, realname=realname)
        location.fill('latitude', location.ULlat)
        location.fill('longitude', location.ULlng)
        location.fill('isleader', isleader)

    def _add_pay_detail(self, **kwargs):
        with db.auto_commit():
            mountprice = kwargs.get('PPpayMount')
            if Decimal(str(mountprice)) <= Decimal('0'):
                mountprice = Decimal('0.01')
            pp = PlayPay.create({
                'PPid': str(uuid.uuid1()),
                'PPpayno': kwargs.get('opayno'),
                'PPpayType': kwargs.get('PPpayType'),
                'PPcontent': kwargs.get('PPcontent'),
                'PPpayMount': mountprice,
            })
            db.session.add(pp)
            return self._pay_detail(kwargs.get('body'), float(mountprice),
                                    kwargs.get('opayno'), kwargs.get('openid'))

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

    def _incount(self, user, price):
        uw = UserWallet.query.filter_by(USid=user.USid, isdelete=False).first()
        if not uw:
            uw = UserWallet.create({
                'UWid': str(uuid.uuid1()),
                'USid': user.USid,
                'UWbalance': Decimal(str(price)),
                'UWtotal': Decimal(str(price)),
                'UWcash': Decimal(str(price)),
            })

        else:
            uw.UWbalance = Decimal(str(uw.UWbalance)) + Decimal(str(price))
            uw.UWtotal = Decimal(str(uw.UWtotal)) + Decimal(str(price))
            uw.UWcash = Decimal(str(uw.UWcash)) + Decimal(str(price))
        db.session.add(uw)

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

    def _auto_playstatus(self, play):
        current_app.logger.info('plid = {} 是否创建异步开启互动任务 {} {}'.format(play.PLid,
                                                                      play.PLstatus == PlayStatus.publish.value,
                                                                      play.PLstatus))

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
            current_app.logger.info('获取到开启活动任务id {}'.format(start_task_id))
            current_app.logger.info('获取到结束活动任务id {}'.format(end_task_id))
            # if conn.get(start_connid):
            #     conn.delete(start_connid)
            # if conn.get(end_connid):
            #     conn.delete(end_connid)
            conn.set(start_connid, start_task_id)
            conn.set(end_connid, end_task_id)

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
        return Play.query.join(EnterLog, EnterLog.PLid == Play.PLid
                               ).filter(Play.isdelete == false(),
                                        Play.PLstatus == PlayStatus.activity.value,
                                        Play.PLstartTime <= now,
                                        Play.PLendTime >= now,
                                        EnterLog.isdelete == false(),
                                        EnterLog.USid == usid,
                                        EnterLog.ELstatus == EnterLogStatus.success.value,
                                        ).first()

    def _refund_to_user(self, out_trade_no, out_request_no, mount, old_total_fee=None):
        """
        执行退款
        mount 单位元
        old_total_fee 单位元
        out_request_no
        :return:
        """

        mount = int(mount * 100)
        old_total_fee = int(Decimal(str(old_total_fee)) * 100)
        current_app.logger.info('the total fee to refund cent is {}'.format(mount))
        result = self.wx_pay.refund(
            out_trade_no=out_trade_no,
            out_refund_no=out_request_no,
            total_fee=old_total_fee,  # 原支付的金额
            refund_fee=mount  # 退款的金额
        )
        return result

    def _pay_to_user(self, cn):
        """
        付款到用户微信零钱
        cn 提现申请记录
        :return:
        """
        user = User.query.filter(User.isdelete == false(),
                                 User.USid == cn.USid,
                                 User.USopenid1.isnot(None)).first_("提现用户状态异常，请检查后重试")
        try:
            result = self.wx_pay.pay_individual(
                partner_trade_no=self.wx_pay.nonce_str,
                openid=user.USopenid1,
                amount=int(Decimal(cn.CNcashNum).quantize(Decimal('0.00')) * 100),
                desc="旗行零钱转出",
                spbill_create_ip=self.wx_pay.remote_addr
            )
            current_app.logger.info('小程序提现到零钱, response: {}'.format(request))
        except Exception as e:
            current_app.logger.error('小程序提现返回错误：{}'.format(e))
            raise StatusError('微信商户平台: {}'.format(e))
        return result

    def _fill_make_over(self, play):
        makeover = MakeOver.query.filter_by(PLid=play.PLid, isdelete=False).first()
        makeover_status = False
        if common_user():
            user = get_current_user()
            if makeover and makeover.MOsuccessor == user.USid:
                makeover_status = True
                # play.fill()
        play.fill('makeover', makeover_status)

    def _opayno(self):
        opayno = self.wx_pay.nonce_str
        pp = PlayPay.query.filter_by(PPpayno=opayno, isdelete=False).first()
        if pp:
            return self._opayno()
        return opayno

    def _enter_log(self, pp):
        # 修改当前用户参加状态
        el = EnterLog.query.filter(EnterLog.ELpayNo == pp.PPpayno, EnterLog.isdelete == false()).first()
        if not el:
            current_app.logger.info('当前报名单不存在 {} '.format(pp.PPpayno))
            return
        el.ELstatus = EnterLogStatus.success.value
        db.session.add(el)
        # 金额进入导游账号

        mount_price = Decimal(str(pp.PPpayMount))
        play = Play.query.filter_by(PLid=el.PLid, isdelete=False).first()
        if not play:
            current_app.logger.info('活动 {} 已删除， {} 正在报名'.format(el.PLid, el.USid))
            # 活动已删除，钱进入用户账户
            user = User.query.filter_by(USid=el.USid, isdelete=False).first()
            if user:
                # 付款用户不存在，钱进入平台
                self._incount(user, mount_price)
            return

        guide = User.query.filter_by(USid=play.PLcreate, isdelete=False).first()
        if not guide:
            # 导游不存在，钱进入平台账户
            current_app.logger.info('导游 {} 已删除, {} 正在报名'.format(play.PLcreate, el.USid))
            return

        self._incount(guide, mount_price)

    def _undertake(self, pp):
        mount_price = Decimal(str(pp.PPpayMount))
        out_trade_no = pp.PPpayno
        makeover = MakeOver.query.filter(MakeOver.MOpayNo == out_trade_no, MakeOver.isdelete == false()).first()
        if not makeover:
            current_app.logger.info('当前转让单不存在 {}'.format(out_trade_no))
            return
        makeover.MOstatus = MakeOverStatus.success.value
        play = Play.query.filter_by(PLid=makeover.PLid, isdelete=False).first()
        if not play:
            # 活动已删除，钱进入用户账户
            current_app.logger.info('活动已删除')
            user = User.query.filter_by(USid=makeover.MOsuccessor, isdelete=False).first()
            if user:
                # 付款用户不存在，钱进入平台
                self._incount(user, mount_price)
            return
        play.PLcreate = makeover.MOsuccessor
        play.PLstatus = PlayStatus.publish.value
        # 删除转让单
        # makeover.isdelete = True

        db.session.add(play)
        db.session.add(makeover)

        # 钱进入原领队账户
        guide = User.query.filter_by(USid=makeover.MOassignor, isdelete=False).first()
        if not guide:
            # 导游不存在，钱进入平台账户
            current_app.logger.info('导游 {} 已删除, {} 正在承接活动'.format(play.PLcreate, makeover.MOsuccessor))
            return
        self._incount(guide, mount_price)
        # 如果存在报名记录，清理掉
        EnterLog.query.filter_by(PLid=play.PLid, USid=makeover.MOsuccessor, isdelete=False).delete_(synchronize_session=False)

    def _fill_mo(self, play, mo, detail=False):
        mo.add('createtime')

        mo.fill('plname', play.PLname)
        mo.fill('PLimg', play.PLimg)
        # mo.fill('PLtitle', play.PLtitle)
        mo.fill('PLnum', play.PLnum)
        mo.fill('mostatus_zh', MakeOverStatus(mo.MOstatus).zh_value)
        mo.fill('mostatus_en', MakeOverStatus(mo.MOstatus).name)
        if detail:
            mo.fill('PLstartTime', play.PLstartTime)
            mo.fill('PLendTime', play.PLendTime)
            mo.fill('enternum', play.enternum)
        assignor = User.query.filter_by(USid=mo.MOassignor, isdelete=False).first()
        successor = User.query.filter_by(USid=mo.MOsuccessor, isdelete=False).first()
        if not assignor:
            current_app.logger.info('{} 的转让人不存在'.format(mo.MOid))
            assignor_name = '旗行官方'

        else:
            assignor_name = assignor.USname
        if not successor:
            current_app.logger.info('{} 的承接人不存在'.format(mo.MOid))
            successor_name = '旗行官方'
        else:
            successor_name = successor.USname

        agreement = Agreement.query.filter_by(AMtype=0, isdelete=False).order_by(Agreement.updatetime.desc()).first()
        content = agreement.AMcontent

        re_c = content.format(assignor_name, play.PLname, play.PLstartTime, play.PLendTime, successor_name,
                              '', mo.MOprice, successor_name, successor_name, mo.createtime)
        mo.fill('agreemen', re_c)
        mo.fill('MOassignor', assignor_name)
        mo.fill('MOsuccessor', successor_name)
