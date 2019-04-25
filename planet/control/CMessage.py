import uuid

from flask import request

from flaskrun import socketio
from planet.common.error_response import AuthorityError, ParamsError
from planet.common.params_validates import parameter_required
from planet.common.success_response import Success
from planet.common.token_handler import token_required, is_admin, is_supplizer, common_user
from planet.config.enums import ProductFrom, PlanetMessageStatus
from planet.extensions.register_ext import db
from planet.models import ProductBrand, User
from planet.models.message import PlatformMessage, UserPlatfromMessage


class CMessage():

    @token_required
    def set_message(self):
        if is_admin():

            pmfrom = ProductFrom.platform.value
        elif is_supplizer():
            # pb = ProductBrand.query.filter(ProductBrand.SUid == request.user.id, ProductBrand.isdelete == False).first()
            #
            # pmhead = pb.PBlogo
            # pmname = pb.PBname
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
                return Success('删除成功', data={'pmid': pmid})
            pmdict = {
                'PMtext': data.get('pmtext'),
                'PMstatus': data.get('pmstatus')
            }
            if not pm:
                pmdict.setdefault('PMcreate', request.user.id)
                pmdict.setdefault('PMid', pmid)
                pmdict.setdefault('PMfrom', pmfrom)
                pm = PlatformMessage.create(pmdict)
                msg = '创建成功'
            else:
                pm.update(pmdict)
                msg = '更新成功'

            # 如果站内信为上线状态，创建用户站内信 todo
            if pm.PMstatus == PlanetMessageStatus.publish:
                user_list = User.query.filter_by(isdelete=False).all()
                instance_list = list()
                for user in user_list:
                    upm = UserPlatfromMessage.create({
                        'UPMid': str(uuid.uuid1()),
                        'USid': user.USid,
                        'PMid': pmid
                    })
                    instance_list.append(upm)

                db.session.add_all(instance_list)
            return Success(msg, data={'pmid': pmid})

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

        return Success(data=pm_list)

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
        pm.fill('pmstatus_zh', PlanetMessageStatus(pm.PMstatus).zh_value)
        pm.fill('pmstatus_eh', PlanetMessageStatus(pm.PMstatus).name)

    @socketio.on('connect', namespace='/change_platfromMessage')
    def change_platfromMessage(self):
        # global thread
        # with thread_lock:
        # if thread is None:
        socketio.start_background_task(target=self.background_thread)

    def background_thread(self):
        while True:
            # socketio.sleep(5)
            # t = random.randint(1, 100)
            upm = UserPlatfromMessage.query.filter_by()
            socketio.emit('server_response',
                          {'data': t}, namespace='/change_platfromMessage')
