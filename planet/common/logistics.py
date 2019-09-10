# -*- coding: utf-8 -*-
import requests
from flask import current_app

from planet.config.secret import kd_api_url, kd_api_code


class Logistics(object):
    """快递查询"""
    def __init__(self):
        self.code = kd_api_code
        self.headers = {
            'Authorization': 'APPCODE {}'.format(self.code)
        }

    def fetch(self, url, arg, method='get', json=True):
        if method == 'get':
            response = requests.get(url, params=arg, headers=self.headers)
        else:
            response = requests.post(url, data=arg, headers=self.headers)

        if response.status_code != 200:
            current_app.logger.error('物流接口请求状态异常，可能是配置错误或者接口挂了; 状态：{} , 接口返回体： {}'.format(response, response.__dict__))
            return
        if json:
            try:
                res = response.json()
                current_app.logger.info('返回物流数据正常 >>> {}'.format(res))
            except Exception as e:
                res = response.text
                current_app.logger.error('返回物流数据异常 >>> {}'.format(e))
        else:
            res = response.text
        return res

    def get_logistic(self, no, type=None):
        """
        快递查询: https://market.aliyun.com/products/56928004/cmapi022273.html
        """
        url = kd_api_url
        params = {
            'no': no,
            'type': type
        }
        response = self.fetch(url, params)
        return response




