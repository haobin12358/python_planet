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
from planet.models import ProductBrand, User, UserPlatfromMessageLog, PlatformMessage, UserPlatfromMessage


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
                    self._push_platform_message_all()

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
                self._push_platform_message_all()

        # current_app.logger.info('结束创建/ 更新站内信 {}'.format(datetime.now()))
        return Success(msg, data={'pmid': pmid})

    @token_required
    def get_platform_message(self):
        data = parameter_required()
        filter_args = {
            PlatformMessage.isdelete == False
        }
        if is_supplizer():
            filter_args.add(PlatformMessage.PMcreate == request.user.id)

        if data.get('PMstatus', None) is not None:
            filter_args.add(PlatformMessage.PMstatus == data.get('pmstatus'))

        pm_list = PlatformMessage.query.filter(*filter_args).order_by(PlatformMessage.createtime.desc()).all_with_page()
        for pm in pm_list:
            self._fill_pm(pm)
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
        if not is_tourist():
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
        usersids = self.get_usersid()
        self.push_platform_message(usid=user.USid, usersid=usersids.get(user.USid))
        return Success()

    def push_platform_message(self, usid, usersid):
        from planet import socketio  # 路径引用需要是局部的 而且只能引用这个

        pm_list = PlatformMessage.query.filter(
            UserPlatfromMessage.isdelete == False,
            PlatformMessage.PMid == UserPlatfromMessage.PMid,
            PlatformMessage.isdelete == False,
            UserPlatfromMessage.USid == usid
        ).order_by(PlatformMessage.createtime.desc()).all()
        for pm in pm_list:
            self._fill_pm(pm)
            self._fill_um(pm, usid)

        socketio.emit('message_list', Success('获取站内信列表成功', data=pm_list), room=usersid)

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
            pb = ProductBrand.query.filter(ProductBrand.SUid == request.user.id, ProductBrand.isdelete == False).first()
            pmhead = pb.PBlogo
            pmname = pb.PBname

        else:
            pmhead = ''
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

    def _push_platform_message_all(self):
        usersid = self.get_usersid()
        # current_app.logger.info('开始推送 {}'.format(datetime.now()))
        for usid in usersid:
            self.push_platform_message(usid, usersid.get(usid))
        # current_app.logger.info('结束推送 {}'.format(datetime.now()))
