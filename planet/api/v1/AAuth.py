# -*- coding: utf-8 -*-
from flask import request, jsonify
from alipay import AliPay

from planet.common.base_resource import Resource
from planet.common.token_handler import usid_to_token
from planet.control.CAuth import CAuth


class AAuth(Resource):
    def __init__(self):
        self.cauth = CAuth()

    def post(self):
        # data = request.json
        # usid = data.get('usid')
        data = request.json or {}
        usid = 'usid1'
        model = data.get('model', 'User')
        token = usid_to_token(usid, model)
        return token

    def get(self, auth):
        apis = {
            'fresh': self.cauth.fresh,
            'cookie_test': self.cauth.cookie_test,
        }
        return apis



