# -*- coding: utf-8 -*-
from planet.common.base_resource import Resource
from testcase.testdata.TDUsers import TDUsers


class ATest(Resource):
    def __init__(self):
        self.test = TDUsers()

    def get(self, test):
        apis = {
            "test_user_data": self.test.test_user_data,
            "test_userlogintime_data": self.test.test_userlogintime_data,
            "test_usercommission_data": self.test.test_usercommission_data
        }
        return apis