# -*- coding: utf-8 -*-
import requests

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
        if json:
            return response.json()
        return response.text

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




