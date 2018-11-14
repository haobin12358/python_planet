# -*- coding: utf-8 -*-

import requests
import json

from planet.config.secret import ID_CHECK_APPCODE

url = 'https://1.api.apistore.cn/idcard3'

method = 'POST'


class DOIDCheck(object):

    result = False
    check_response = None

    def __init__(self, name, idcode):
        """
        执行身份实名认证
        :param name:
        :param idcode:
        """
        self.name = name
        self.idcode = idcode
        self._get_check_response()

    def _get_check_response(self):
        bodys = {}
        bodys['cardNo'] = self.idcode
        bodys['realName'] = self.name
        header = {
            "Authorization": 'APPCODE ' + ID_CHECK_APPCODE,
            'Content-Type': 'application/x-www-form-urlencoded; charset=UTF-8' }
        request = requests.post(url, data=bodys, headers=header)
        if request.status_code != 200:
            self.result = False
            self.check_response = {
                "error_code": 80008,
                "reason": "身份证中心维护，请稍后重试",
            }
        else:
            self.check_response = json.loads(request.text)
            print('get id check response :', self.check_response)
            if self.check_response.get("error_code") == 0:
                self.result = True
            else:
                self.result = False


if __name__ == '__main__':
    result = DOIDCheck('刘帅斌', '620523199510080011').result
    print(result)
