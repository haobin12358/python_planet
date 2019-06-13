import ast
import uuid
from datetime import datetime

from flask import request, current_app

# from flaskrun import socketio
from flask_socketio import SocketIO

# from flaskrun import sids
from planet.common.error_response import AuthorityError, ParamsError, StatusError
from planet.common.params_validates import parameter_required
from planet.common.success_response import Success
from planet.common.token_handler import token_required, is_admin, is_supplizer, common_user, get_current_user, \
    is_tourist
from planet.config.enums import ProductFrom, PlanetMessageStatus, AdminActionS, UserPlanetMessageStatus
from planet.control.BaseControl import BASEADMIN
from planet.extensions.register_ext import db, conn
from planet.models import ProductBrand, User, UserPlatfromMessageLog, PlatformMessage, UserPlatfromMessage, Admin, News, \
    Supplizer, UserRoom, Room, UserMessage


class CMessage():

    @token_required
    def set_message(self):
        current_app.logger.info('开始创建/ 更新站内信 {}'.format(datetime.now()))
        if is_admin():

            pmfrom = ProductFrom.platform.value
        elif is_supplizer():
            pmfrom = ProductFrom.supplizer.value
        else:
            raise AuthorityError

        # data = parameter_required(('PMtext', ))
        data = parameter_required()
        pmid = data.get('pmid') or str(uuid.uuid1())
        with db.auto_commit():
            pm = PlatformMessage.query.filter_by(PMid=pmid, isdelete=False).first()
            if data.get('delete'):
                if not pm:
                    raise ParamsError('站内信已删除')
                pm.update({'isdelete': True})
                db.session.add(pm)

                # 如果有上线站内信，同时删除已经发送给用户的站内信，并更新
                if pm.PMstatus == PlanetMessageStatus.publish.value:
                    UserPlatfromMessage.query.filter_by(PMid=pm.PMid).delete_()
                    # self._push_platform_message_all()

                if is_admin():
                    BASEADMIN().create_action(AdminActionS.delete.value, 'PlatformMessage', pmid)
                current_app.logger.info('结束 删除站内信 {}'.format(datetime.now()))
                return Success('删除成功', data={'pmid': pmid})
            pmdict = {
                'PMtext': data.get('pmtext'),
                'PMtitle': data.get('pmtitle'),
                'PMstatus': data.get('pmstatus')
            }
            if not pm:
                pmdict.setdefault('PMcreate', request.user.id)
                pmdict.setdefault('PMid', pmid)
                pmdict.setdefault('PMfrom', pmfrom)
                pm = PlatformMessage.create(pmdict)
                if is_admin():
                    BASEADMIN().create_action(AdminActionS.insert.value, 'PlatformMessage', pmid)
                msg = '创建成功'
            else:
                if pm.PMstatus == PlanetMessageStatus.publish.value:
                    raise StatusError('已上线站内信不能修改')
                pm.update(pmdict)
                if is_admin():
                    BASEADMIN().create_action(AdminActionS.update.value, 'PlatformMessage', pmid)
                msg = '更新成功'
            current_app.logger.info('结束 创建/ 更新站内信内容 {}'.format(datetime.now()))
            db.session.add(pm)

            # 如果站内信为上线状态，创建用户站内信 推送 todo 状态判断导致点编辑看看会刷新用户记录，待完善需求
            if pm.PMstatus == PlanetMessageStatus.publish.value:
                # 创建用户站内信
                # current_app.logger.info('开始创建 用户 站内信 {}'.format(datetime.now()))
                # todo 待优化，此处 2690+用户时 创建需要21~23s
                user_list = User.query.filter_by(isdelete=False).all()
                instance_list = list()
                for user in user_list:
                    upm = UserPlatfromMessage.query.filter_by(PMid=pmid, USid=user.USid, isdelete=False).first()
                    if not upm:
                        upm = UserPlatfromMessage.create({
                            'UPMid': str(uuid.uuid1()),
                            'USid': user.USid,
                            'PMid': pmid
                        })
                    else:
                        upm.update({'UPMstatus': UserPlanetMessageStatus.unread.value})
                    instance_list.append(upm)

                db.session.add_all(instance_list)
                db.session.flush()
                # current_app.logger.info('结束 创建/用户站内信 {}'.format(datetime.now()))
                # 推送
                self._push_platform_message_all(pmid)

        # current_app.logger.info('结束创建/ 更新站内信 {}'.format(datetime.now()))
        return Success(msg, data={'pmid': pmid})

    @token_required
    def get_platform_message(self):
        data = parameter_required()
        filter_args = {
            PlatformMessage.isdelete == False
        }
        if common_user():
            filter_args.add(PlatformMessage.PMstatus == PlanetMessageStatus.publish.value)
        if is_supplizer():
            filter_args.add(PlatformMessage.PMcreate == request.user.id)

        if data.get('PMstatus', None) is not None:
            filter_args.add(PlatformMessage.PMstatus == data.get('pmstatus'))

        pm_list = PlatformMessage.query.filter(*filter_args).order_by(PlatformMessage.createtime.desc()).all_with_page()
        for pm in pm_list:
            self._fill_pm(pm)
            if common_user():
                self._fill_um(pm, request.user.id)
            else:
                um_read_count = UserPlatfromMessage.query.filter(
                    UserPlatfromMessage.isdelete == False,
                    UserPlatfromMessage.PMid == pm.PMid,
                    UserPlatfromMessage.UPMstatus == UserPlanetMessageStatus.read.value
                ).count()
                pm.fill('pmreadcount', um_read_count)

        return Success(data=pm_list)

    @token_required
    def read(self):
        data = parameter_required(('pmid',))
        if not common_user():
            raise AuthorityError
        user = get_current_user()
        with db.auto_commit():
            upm = UserPlatfromMessage.query.filter_by(PMid=data.get('pmid'), USid=user.USid, isdelete=False).first()
            upml = UserPlatfromMessageLog.create({
                'UPMLid': str(uuid.uuid1()),
                'UPMid': upm.UPMid,
                'USid': user.USid
            })

            if upm.UPMstatus != UserPlanetMessageStatus.read.value:
                upm.UPMstatus = UserPlanetMessageStatus.read.value

            db.session.add(upml)
            db.session.add(upm)
        # usersids = self.get_usersid()
        # self.push_platform_message(usid=user.USid, usersid=usersids.get(user.USid))
        return Success()

    def push_platform_message(self, pmid, usid, usersid):
        from planet import socketio  # 路径引用需要是局部的 而且只能引用这个

        filter_args = {
            UserPlatfromMessage.isdelete == False,
            PlatformMessage.PMid == UserPlatfromMessage.PMid,
            PlatformMessage.isdelete == False,
            PlatformMessage.PMstatus == PlanetMessageStatus.publish.value,
            UserPlatfromMessage.USid == usid
        }
        if pmid:
            filter_args.add(PlatformMessage.PMid == pmid)
        pm = PlatformMessage.query.filter(*filter_args).order_by(PlatformMessage.createtime.desc()).first()
        # for pm in pm_list:
        self._fill_pm(pm)
        self._fill_um(pm, usid)

        socketio.emit('message_list', Success('获取站内信列表成功', data=pm), room=usersid)

    def test(self):
        # from flaskrun import socketio
        from planet import socketio
        # socketio = SocketIO(message_queue='')
        t = '后台主动请求'
        # socketio.start_background_task(target=self.background_test, socket=socketio)
        # conn.delete('sids')
        # sid_dict = conn.get('sids') or {}
        # if sid_dict:
        #     sid_list = ast.literal_eval(str(sid_dict, encoding='utf-8'))
        sid_dict = self.get_usersid()

        for usid in sid_dict:
            socketio.emit('test', {'data': t}, room=sid_dict.get(usid))

        # socketio.emit('test', {'data': t}, broadcast=True)
        return 'true'

    def get_usersid(self):
        # current_app.logger.info('start get user sids {}'.format(datetime.now()))
        usersids = conn.get('usersid') or {}  # usersids 格式 {userid: sid}
        if usersids:
            usersids = ast.literal_eval(str(usersids, encoding='utf-8'))
        # current_app.logger.info('get usersids {}'.format(usersids))
        # current_app.logger.info('end get user sids {}'.format(datetime.now()))
        return usersids

    def _fill_pm(self, pm):
        if pm.PMfrom == ProductFrom.supplizer:
            pb = ProductBrand.query.filter(ProductBrand.SUid == pm.PMcreate, ProductBrand.isdelete == False).first()
            pmhead = pb.PBlogo
            pmname = pb.PBname

        else:
            admin = Admin.query.filter_by(ADid=pm.PMcreate, isdelete=False).first()
            pmhead = admin['ADheader'] if admin else 'https://pre2.bigxingxing.com/img/logo.png'
            pmname = '大行星官方'
        pm.fill('pmhead', pmhead)
        pm.fill('pmname', pmname)
        pm.add('createtime')
        pm.fill('pmstatus_zh', PlanetMessageStatus(pm.PMstatus).zh_value)
        pm.fill('pmstatus_eh', PlanetMessageStatus(pm.PMstatus).name)

    def _fill_um(self, pm, usid):
        um = UserPlatfromMessage.query.filter(UserPlatfromMessage.PMid == pm.PMid, UserPlatfromMessage.USid == usid,
                                              UserPlatfromMessage.isdelete == False).order_by(
            UserPlatfromMessage.createtime.desc()).first()
        pm.fill('umstatus', um.UPMstatus)
        pm.fill('umstatus_zh', UserPlanetMessageStatus(um.UPMstatus).zh_value)
        pm.fill('umstatus_en', UserPlanetMessageStatus(um.UPMstatus).name)
        # pm.fill('umstatus', um.UPMstatus)

    def _push_platform_message_all(self, pmid):
        usersid = self.get_usersid()
        # current_app.logger.info('开始推送 {}'.format(datetime.now()))
        for usid in usersid:
            self.push_platform_message(pmid, usid, usersid.get(usid))
        # current_app.logger.info('结束推送 {}'.format(datetime.now()))

    @token_required
    def create_room(self):
        if not common_user():
            raise AuthorityError
        user = get_current_user()
        data = parameter_required()
        roomid = self.get_room(data, user)
        return Success(data=roomid)

    @token_required
    def get_room_list(self):
        user_room_list = UserRoom.query.join(Room, Room.ROid == UserRoom.ROid).filter(
            UserRoom.USid == request.user.id,
            UserRoom.isdelete == False,
            UserRoom.URshow == True,
            Room.isdelete == False).order_by(
            Room.updatetime.desc()).all_with_page()
        for user_room in user_room_list:
            room = Room.query.filter_by(ROid=user_room.ROid, isdelete=False).first()

            user_message = UserMessage.query.filter(
                UserMessage.ROid == user_room.ROid,
                UserMessage.isdelete == False
            ).order_by(UserMessage.createtime.desc()).first()
            other_list = UserRoom.query.filter(
                UserRoom.ROid==user_room.ROid, UserRoom.isdelete==False, UserRoom.USid != user_room.USid).all()
            roomname = ""
            head_list = list()
            for other in other_list:
                user = User.query.filter_by(USid=other.USid, isdelete=False).first()
                if user:
                    roomname += user.USname
                    head_list.append(user['USheader'])
                else:
                    roomname += '未知'
                    head_list.append('https://pre2.bigxingxing.com/img/logo.png')
                # other_dict_list.append({'usname', })
            user_room.fill('umsgtext', user_message.UMSGtext if user_message else "")
            user_room.fill('umsgtype', user_message.UMSGtype if user_message else 0)
            user_room.fill('headlist', head_list)
            user_room.fill('roomname', roomname)
            user_room.fill('updatetime', room.updatetime if room else user_room.updatetime)
            user_room.hide('USid')

        return Success(data=user_room_list)

    def get_room(self, data, userid):
        neid = data.get('neid')
        usid = data.get('usid')
        roid = data.get('roid')
        if roid:
            roomid = roid
        else:

            if neid:
                news = News.query.filter_by(NEid=neid, isdelete=False).first_('用户不存在')
                usid = news.USid

            # 获取当前用户有的房间
            room_list = UserRoom.query.filter_by(USid=userid, isdelete=False).all()
            roomid = None
            for room in room_list:
                other_user = UserRoom.query.filter(
                    UserRoom.ROid == room.ROid,
                    UserRoom.USid != userid,
                    UserRoom.isdelete == False).all()
                other_user_id = [other.USid for other in other_user]
                # 如果有和对方聊天的双人房间 返回房间id
                if usid in other_user_id and len(other_user_id) == 1:
                    roomid = room.ROid
        with db.auto_commit():
            if not roomid:
                # 如果不存在和对方的聊天房间 则创建房间
                roomid = str(uuid.uuid1())
                # room =
                db.session.add(Room.create({'ROid': roomid}))
                # 同时添加双方信息
                db.session.add(UserRoom.create({
                    "URid": str(uuid.uuid1()),
                    'USid': userid,
                    'ROid': roomid
                }))
                db.session.add(UserRoom.create({
                    "URid": str(uuid.uuid1()),
                    'USid': usid,
                    'ROid': roomid
                }))
            else:
                UserRoom.query.filter_by(ROid=roomid, isdelete=False).update({'URshow': True})

        return roomid

    def send_msg(self, umsgtext, umsgtype, roomid, userid):
        umsg = UserMessage.create({
            'UMSGid': str(uuid.uuid1()),
            'USid': userid,
            'ROid': roomid,
            'UMSGtext': umsgtext,
            'UMSGtype': umsgtype,
        })

        from planet import socketio
        with db.auto_commit():
            db.session.add(umsg)
            self._fill_umsg(umsg)
            room = Room.query.filter_by(ROid=roomid, isdelete=False).first()
            um_list = UserRoom.query.filter(
                UserRoom.ROid == roomid,
                UserRoom.USid != userid,
                UserRoom.isdelete == False
            ).all()
            usersid = self.get_usersid()
            for um in um_list:
                user = User.query.filter_by(USid=um.USid, isdelete=False).first()
                admin = Admin.query.filter_by(ADid=um.USid, isdelete=False).first()
                usunread = 0
                if user:
                    user.USunread = (user.USunread or 0) + 1
                    usunread = user.USunread
                if admin:
                    admin.ADunread = (admin.ADunread or 0) + 1
                    usunread = admin.ADunread

                um.URunread = (um.URunread or 0) + 1
                umsg.fill('usunread', usunread)
                umsg.fill('urunread', um.URunread)

                socketio.emit('notice', umsg, room=usersid.get(um.USid))

            room.updatetime = datetime.now()
        return umsg

    @token_required
    def get_message_list(self):
        data = parameter_required()
        roomid = data.get('roid')
        umsg_list = UserMessage.query.filter(UserMessage.ROid == roomid, UserMessage.isdelete == False).order_by(
            UserMessage.createtime.desc()).all_with_page()
        um = UserRoom.query.filter_by(USid=request.user.id, ROid=roomid).first()
        with db.auto_commit():
            for umsg in umsg_list:
                self._fill_umsg(umsg, is_get=True, urunread=um.URunread)
            um.URunread = 0

        return Success(data=umsg_list)

    def _fill_umsg(self, umsg, is_get=False, urunread=0):
        user = User.query.filter_by(USid=umsg.USid).first()
        admin = Admin.query.filter_by(ADid=umsg.USid).first()
        # unread = 0
        # supplizer = Supplizer.query.filter_by(SUid=umsg.USid).first()
        if not (user or admin):
            head = 'https://pre2.bigxingxing.com/img/logo.png'
            name = '大行星官方'
        else:
            if user:
                head = user['USheader']
                name = user.USname
                if is_get:
                    user.USunread -= urunread
                    if user.USunread < 0:
                        user.USunread = 0
                # else:
                    # user.USunread = (user.USunread or 0) + 1
                    # unread = user.USunread
            else:
                head = admin['ADheader']
                name = admin.ADname
                if is_get:
                    admin.ADunread -= urunread
                    if admin.ADunread < 0:
                        admin.ADunread = 0
                # else:
                    # admin.ADunread = (admin.ADunread or 0) + 1
                    # unread = admin.ADunread

        umsg.fill('head', head)
        if not is_tourist():
            umsg.fill('isself', user.USid == request.user.id)
        umsg.fill('name', name)
        umsg.add('createtime')
        # return unread

    @token_required
    def del_room(self):
        data = parameter_required(('roid',))
        roid = data.get('roid')
        usid = request.user.id
        ur = UserRoom.query.filter_by(USid=usid, ROid=roid, URshow=True).first()
        if not ur:
            return Success('已经删除')
        with db.auto_commit():
            ur.URshow = False

        return Success('删除成功')



