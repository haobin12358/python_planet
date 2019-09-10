# from enums import TemplateID
from flask import current_app
from sqlalchemy import false

from planet.config.enums import TemplateID
from planet.extensions.register_ext import mp_miniprogram
from planet.extensions.weixin import WeixinMP
from planet.models import User, Play, EnterLog


def log(fn):
    def inner(*args, **kwargs):
        result = fn(*args, **kwargs)
        current_app.logger.info('get wx response = {}'.format(result))

    return inner


class CTemplates(object):
    def __init__(self):
        self.mp_miniprogram = mp_miniprogram

    @log
    def enter(self, elid, form_id):
        # 用户报名参加，通知到领队
        tempid = TemplateID.enter.zh_value

        # 获取领队信息
        leader = User.query.join(EnterLog, EnterLog.USid == User.USid).filter(EnterLog.ELid == elid).first()
        # el = EnterLog.query.filter(EnterLog.ELid == elid, EnterLog.isdelete == false()).first()
        # user =
        if not leader or not leader.USopenid1:
            current_app.logger.info('没有活动用户 elid = {}'.format(elid))
            return
        data = {
            "keyword1": {
                "value": "某个热心网友发来贺电"
            },
            "keyword2": {
                "value": "就这个活动带他一起"
            }
        }
        return self.mp_miniprogram.template_send(tempid, leader.USopenid1, data, page='/pages/index/manageActivity', form_id=form_id)

    def cancel(self):
        pass

    def gather(self):
        pass

    def activity(self):
        pass

    def signin(self):
        pass

    def setsignin(self):
        pass

    def makeover(self):
        pass

    def toilet(self):
        pass

    def accomplished(self):
        pass

    def guide(self):
        pass

    def agreement(self):
        pass
