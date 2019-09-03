# -*- coding: utf-8 -*-

import uuid
import hmac
import base64
import datetime
import json
import time
import urllib
import requests
from hashlib import sha1

from planet.common.error_response import ParamsError
from planet.common.request_handler import gennerc_log
from ..config.secret import ACCESS_KEY_ID, ACCESS_KEY_SECRET, SignName, TemplateCode
# from ..config.cfgsetting import singleton


# @singleton
class SendSMS:
    prefix_url = "https://dysmsapi.aliyuncs.com/?"

    def __init__(self, reciver, _tpl_params, sign_name=SignName, templatecode=TemplateCode):
        """
        发送阿里云短信
        :param reciver: 接受人电话
        :param _tpl_params: {code: '123456'}
        :param sign_name: 签名
        :param templatecode: 短信模板(默认为验证码模板)
        """
        self._send_sms_ali(reciver, _tpl_params, sign_name, templatecode)

    def params(self, mobiles, tpl_params, sign_name, templatecode):
        p = [
            ["SignatureMethod", "HMAC-SHA1"],
            ["SignatureNonce", uuid.uuid4().hex],
            ["AccessKeyId", ACCESS_KEY_ID],
            ["SignatureVersion", "1.0"],
            ["Timestamp", self.time_now_fmt()],
            ["Format", "JSON"],

            ["Action", "SendSms"],
            ["Version", "2017-05-25"],
            ["RegionId", "cn-hangzhou"],
            ["PhoneNumbers", "{0}".format(mobiles)],
            ["SignName", sign_name],
            ["TemplateParam", json.dumps(tpl_params, ensure_ascii=False)],
            ["TemplateCode", templatecode],
            ["OutId", "123"],
        ]
        return p

    @staticmethod
    def time_now_fmt():
        r = datetime.datetime.utcfromtimestamp(time.time())
        r = time.strftime("%Y-%m-%dT%H:%M:%SZ", r.timetuple())
        return r

    def special_url_encode(self, s):
        r = urllib.parse.quote_plus(s).replace("+", "%20").replace("*", "%2A").replace("%7E", "~")
        return r

    def encode_params(self, lst):
        s = "&".join(list(map(
            lambda p: "=".join([self.special_url_encode(p[0]), self.special_url_encode(p[1])]),
            sorted(lst, key=lambda p: p[0])
        )))
        return s

    def prepare_sign(self, s):
        r = "&".join(["GET", self.special_url_encode("/"), self.special_url_encode(s)])
        return r

    def sign(self, prepare_str):
        k = "{0}{1}".format(ACCESS_KEY_SECRET, "&")
        r = hmac.new(k.encode(), prepare_str.encode(), sha1).digest()
        base_str = base64.b64encode(r).decode()
        return self.special_url_encode(base_str)

    def _send_sms_ali(self, mobiles, tpl_params, sign_name, templatecode):
        params_lst = self.params(mobiles, tpl_params, sign_name, templatecode)
        eps = self.encode_params(params_lst)
        prepare_str = self.prepare_sign(eps)
        sign_str = self.sign(prepare_str)

        url = "{0}Signature={1}&{2}".format(self.prefix_url, sign_str, eps)

        r = requests.get(url)
        if r.status_code != 200:
            raise ParamsError('短信验证获取失败')
        else:
            jn = json.loads(r.text)
            gennerc_log('get sms response : {0}'.format(jn))
            if jn.get("Code") == "OK":
                return True
            else:
                raise ParamsError('短信验证获取失败')


if __name__ == "__main__":
    SendSMS("13588046135", '123456')
