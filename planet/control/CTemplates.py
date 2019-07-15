from enums import TemplateID
from planet.extensions.register_ext import mp_miniprogram
from planet.extensions.weixin import WeixinMP


class CTemplates(object):
    def __init__(self):
        self.mp_miniprogram = mp_miniprogram

    def enter(self):
        # 用户报名参加，通知到领队
        tempid = TemplateID()
        pass

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
