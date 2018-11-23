# -*- coding: utf-8 -*-
from datetime import datetime, date

import requests


class ShareStock:
    url = 'http://hq.sinajs.cn/list={}'
    code = 'sh000002'
    json = False

    def __init__(self, code=None, url=None):
        """
        股票
        :param code: 编码
        """
        if code:
            self.code = code
        if url:
            self.url = url
        self.response = self.get_response()

    def fetch(self, url, json):
        response = requests.get(url)
        if json:
            return response.json()
        return response.text

    def get_response(self):
        res = self.fetch(self.url.format(self.code), self.json)
        values = res.split('=')[-1]
        self.value_list = values.strip('"').split(',')
        return res

    def new_result(self):
        """最新开盘"""
        time_now = datetime.now()
        today = date.today().strftime('%Y%m%d')
        today16hourstr = today + '160000'
        today16hourtime = datetime.strptime(today16hourstr, '%Y%m%d%H%M%S')
        if time_now > today16hourtime:
            # 今日
            self.today_result = format(float(self.value_list[3]), '.2f')
        # 昨日
        self.yesterday_result = format(float(self.value_list[1]), '.2f')
        return self.yesterday_result


if __name__ == '__main__':
    res = ShareStock()

