# -*- coding:utf8 -*-
# from weixin.mp import WeixinMP
import datetime
import urllib2
import json
from WeiDian.config.urlconfig import get_jsapi, get_server_access_token
from WeiDian.config.response import NETWORK_ERROR
from WeiDian.common.import_status import import_status
from WeiDian.common.timeformat import format_for_db
from WeiDian import logger


# mp = WeixinMP(APP_ID, APP_SECRET_KEY)
class weixinmp():

    def __init__(self):
        from WeiDian.common.divide import Partner
        self.pt = Partner()

        self.access_token_server, self.ticket, self.access_time = self.pt.access_token

    def update_access_token_and_jsticket(self, refresh=False):
        now = datetime.datetime.now()
        if refresh:
            self.__refush_access_token_jsticket(now)
            return
        access_time = datetime.datetime.strptime(self.access_time, format_for_db) \
            if self.access_time else datetime.datetime.now()

        delta_time = (now - access_time).seconds
        if not self.ticket or delta_time > 60 * 60 * 2:
            self.__refush_access_token_jsticket(now)

    def __refush_access_token_jsticket(self, now):
        access_token_server_res = self.get_wx_response(get_server_access_token, "get server access token")
        if "access_token" not in access_token_server_res:
            logger.error("get access token server error : %s", access_token_server_res)
            raise NETWORK_ERROR
        self.access_token_server = access_token_server_res.get("access_token")

        jsapiticket = self.get_wx_response(get_jsapi.format(self.access_token_server), "get jsapi_ticket")

        if jsapiticket.get("errcode") == 0 and jsapiticket.get("errmsg") == "ok":
            self.ticket = jsapiticket.get("ticket")
        else:
            logger.error("get jsapi error :  %s", jsapiticket)
            return import_status("get_jsapi_error", "WD_ERROR", "error_get_jsapi")
        self.access_time = now.strftime(format_for_db)
        self.pt.access_token = (self.access_token_server, self.ticket, self.access_time)

    def accesstoken(self):
        self.update_access_token_and_jsticket()
        return self.access_token_server

    def jsticket(self):
        self.update_access_token_and_jsticket()
        return self.ticket

    def get_wx_response(self, url, urltype):
        try:
            req = urllib2.Request(url)
            response = urllib2.urlopen(req)
            strResult = response.read()
            response.close()
            logger.info("%s is %s", urltype, strResult)
            return json.loads(strResult)
        except:
            logger.exception("%s error", urltype)
            raise NETWORK_ERROR


mp = weixinmp()