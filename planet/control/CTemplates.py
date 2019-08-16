# from enums import TemplateID
import time

from flask import current_app
from sqlalchemy import false

from planet.config.enums import TemplateID
from planet.extensions.register_ext import mp_miniprogram
from planet.extensions.weixin import WeixinMP
from planet.models import User, Play, EnterLog


def log(fn):
    def inner(*args, **kwargs):
        # try:

        result = fn(*args, **kwargs)
        current_app.logger.info('get wx response = {}'.format(result))

    # except Exception as e:
    #     current_app.logger.info('error response = {}'.format(e.args))
    #     time.sleep(10)
    #     return inner(*args, **kwargs)

    return inner


class CTemplates(object):
    def __init__(self):
        self.mp_miniprogram = mp_miniprogram

    @log
    def enter(self, el, form_id):
        # 表单信息未获取，无法发送
        if not form_id:
            return
        # 用户报名参加，短信通知到领队 微信模板通知到个人
        tempid = TemplateID.enter.zh_value

        # 获取领队信息
        user = User.query.join(EnterLog, EnterLog.USid == User.USid).filter(EnterLog.ELid == el.ELid).first()

        play = Play.query.filter(Play.PLid == el.PLid, Play.isdelete == false()).first()
        if not play:
            current_app.logger.info('没有活动或活动已删除 elid = {}'.format(el.ELid))
            return
        leader = User.query.filter(User.USid == play.PLcreate, User.isdelete == false()).first()
        if not user or not user.USopenid1:
            current_app.logger.info('没有活动用户 elid = {}'.format(el.ELid))
            return
        if not leader or not leader.USopenid1:
            current_app.logger.info('没有活动领队 elid = {}'.format(el.ELid))
            return

        data = {
            "keyword1": {
                "value": el.createtime
            },
            "keyword2": {
                "value": leader.USname
            },
            "keyword3": {
                "value": "恭喜您已成功加入活动!"
            },
            "keyword4": {
                "value": play.PLname
            },
            "keyword5": {
                "value": play.PLstartTime
            },
            "keyword6": {
                "value": leader.UStelphone
            }
        }
        # todo 短信通知领队
        for i in range(3):
            try:
                wxresponse = self.mp_miniprogram.template_send(
                    tempid, user.USopenid1, data, page='/pages/index/manageActivity', form_id=form_id)
            except Exception as e:
                current_app.logger.info('get error from wx {}'.format(e.args))
                time.sleep(10 + i * 10)
                continue
            return wxresponse
        return self.mp_miniprogram.template_send(
            tempid, user.USopenid1, data, page='/pages/index/manageActivity', form_id=form_id)
        # return

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
