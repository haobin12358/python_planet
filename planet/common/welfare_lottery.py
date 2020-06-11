# -*- coding: utf-8 -*-
import re
import time

import requests
import datetime
from flask import current_app


class WelfareLottery(object):
    url = 'http://www.cwl.gov.cn/cwl_admin/kjxx/findDrawNotice'
    url_backup = 'http://kaijiang.zhcw.com/zhcw/html/3d/list_1.html'
    kaicai_url = 'http://f.apiplus.net/fc3d-1.json'

    proxies = {
        "http": "http://163.204.243.80:9999",
        "https": "https://183.128.141.213:8188",
    }

    headers = {"Accept": "application/json, text/javascript, */*; q=0.01",
               "Accept-Encoding": "gzip, deflate",
               "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
               "Connection": "close",
               "Cookie": "",
               "Host": "www.cwl.gov.cn",
               "Referer": "http://www.cwl.gov.cn/kjxx/fc3d/kjgg",
               "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) "
                             "Chrome/74.0.3729.131 Safari/537.36",
               "X-Requested-With": "XMLHttpRequest"
               }

    headers_backup = {
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;"
                  "q=0.8,application/signed-exchange;v=b3",
        "Accept-Encoding": "gzip, deflate",
        "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
        "Cache-Control": "max-age=0",
        "Connection": "close",
        "Host": "kaijiang.zhcw.com",
        "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko)"
                      " Chrome/74.0.3729.131 Safari/537.3"}

    base_headers = {"User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko)"
                                  " Chrome/74.0.3729.131 Safari/537.3"}

    def __init__(self):
        # today = datetime.date.today() - datetime.timedelta(days=1)
        self.today = datetime.date.today()

    @staticmethod
    def fetch(url, headers, data=None, json=False):
        try:
            response = requests.get(url=url, headers=headers, params=data, timeout=60)
        except requests.exceptions.ConnectionError:
            current_app.logger.info("url connect failed!")
            return
        if response.status_code != 200:
            current_app.logger.error(response.__dict__)
            return
        if json:
            return response.json()
        return response.text

    def get_response(self):
        data = {"name": "3d",
                "issueCount": "",
                "issueStart": "",
                "issueEnd": "",
                "dayStart": str(self.today),
                "dayEnd": str(self.today),
                "pageNo": "",
                "MmEwMD": """3m9Z7Gm5LyH_racZ.qXLxjmUudh1sqwf4a8PJbUCJOkfCzAb23zp_JjQUoLh89jokkEkxqqenNswVMigop1Qk
                2xn7LaZbx8iVsjn04uILeUYIAejjmrREjGAFgUDeWhfTxiaoCzCBPfIBrf2WwzbnnE32_fJIHbJdbYeNfLFAYc5TCACZvJkaqeB
                ZuCVLXgLCdJXGwkrwA9BVXFbuaAQdMkiwqRVC1ocWnEGHtO6aDIRG4WqxgRtUDvmwZuQ_RsI31UWbTHEi2GygRQA91kvz5KwtPj
                EjjINESh22drnCH7P6qdsYPOMsqwcpNO4hVdWWcaiEqoU9Js5uD5PI7WsTWZYpgvP8dyvW6tD22VUfpD137ATQkXNXAT7I7I_Cy
                QGZo14uw.0NBvnVbHBWtNqVeMkdEIditBejV5pRaesfef1rud"""
                }
        res = self.fetch(self.url, self.headers, data, json=True)
        if not res:
            current_app.logger.error('今日福彩官网连接异常：{}'.format(self.today))
            return self.kaicai_api()
        current_app.logger.info('Welfare Lottery 3D {} ：{}'.format(self.today, res.get('message')))
        result = res.get('result') or {}
        if result:
            result = result[0]
        nums = result.get('red')
        date = result.get('date', self.today.strftime('%Y-%m-%d'))[:10]
        code = result.get('code')
        if not (date and code and nums):
            current_app.logger.error('福彩官网数据异常: {}'.format(result))
            return self.kaicai_api()
        resp = [date, code]
        resp.extend(nums.split(','))
        return resp

    def back_up_response(self):
        current_app.logger.info('>>> 尝试从中彩网获取数据 <<<')
        res = self.fetch(self.url_backup, self.headers_backup)
        if not res:
            current_app.logger.error('今日中彩网连接异常：{}'.format(self.today))
            return self.kaicai_api()
        res = re.sub(r'\s', '', res)
        reg = re.compile(r'^.*<tr><tdalign="center">({})</td><tdalign="center">(.*?)</td><tdalign="center"'
                         r'style="padding-left:20px;"><em>(.?)</em><em>(.?)</em><em>(.?)</em></td>.*$'.format(self.today
                                                                                                              ), re.S)
        result = re.findall(reg, res)

        if not result:
            current_app.logger.error('中彩网数据异常：{}'.format(result))
            return self.kaicai_api()
        result = result[0]
        current_app.logger.info('中彩网获得数据: {}'.format(result))
        return result

    def kaicai_api(self):
        current_app.logger.info('>>> 尝试从开彩网获取数据 <<<')
        res = self.fetch(self.kaicai_url, self.base_headers, json=True)
        if not res:
            current_app.logger.error('今日开彩网连接异常：{}'.format(self.today))
            # time.sleep(5)
            # return self.back_up_response()
        data = res.get('data')
        current_app.logger.info('开彩网获得数据: {}'.format(data))
        if not (isinstance(data, list) and len(data) > 0):
            time.sleep(5)
            # return self.back_up_response()
        expect = data[0].get('expect')
        opencode = data[0].get('opencode')
        opentime = data[0].get('opentime')
        if opentime[:10] == str(self.today):
            resp = [opentime[:10], expect]
            resp.extend(opencode.split(','))
            current_app.logger.info('kaicai return data：{}'.format(resp))
            return resp
        # time.sleep(5)
        # return self.back_up_response()


if __name__ == '__main__':
    from planet import create_app

    app, _ = create_app()
    with app.app_context():
        # WelfareLottery().get_response()
        # WelfareLottery().back_up_response()
        WelfareLottery().kaicai_api()