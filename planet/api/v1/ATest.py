# -*- coding: utf-8 -*-
from planet.common.base_resource import Resource
from testcase.testdata.TDUsers import TDUsers


class ATest(Resource):
    def __init__(self):
        self.test = TDUsers()

    def get(self, test):
        apis = {
            "test_user_data": self.test.test_user_data
        }
        return apis