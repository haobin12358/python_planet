# -*- coding: utf-8 -*-
from flask import request

from planet.common.base_resource import Resource
from planet.common.token_handler import usid_to_token


class AAuthTest(Resource):
    """临时登录"""
    def post(self):
        # data = request.json
        # usid = data.get('usid')
        usid = 'usid1'
        token = usid_to_token(usid)
        return token

