import uuid

from flask import request

from planet.common.error_response import AuthorityError, ParamsError
from planet.common.params_validates import parameter_required
from planet.common.success_response import Success
from planet.common.token_handler import token_required, is_admin, is_supplizer
from planet.config.enums import ProductFrom, PlanetMessageStatus
from planet.extensions.register_ext import db
from planet.models import ProductBrand
from planet.models.message import PlatformMessage


class CMessage():

    @token_required
    def set_message(self):
        if is_admin():
            pmhead = ''
            pmname = '大行星官方'
            pmfrom = ProductFrom.platform.value
        elif is_supplizer():
            pb = ProductBrand.query.filter(ProductBrand.SUid == request.user.id, ProductBrand.isdelete == False).first()

            pmhead = pb.PBlogo
            pmname = pb.PBname
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
                pass



