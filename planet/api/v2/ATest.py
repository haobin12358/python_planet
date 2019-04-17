# -*- coding: utf-8 -*-
from planet.common.base_resource import Resource
from testcase.testdata.TDUsers import TDUsers
from testcase.testdata.TDProducts import TDProducts
from testcase.testdata.auto_complete_order import Test

class ATest(Resource):
    def __init__(self):
        self.test = TDUsers()
        self.testproduct = TDProducts()
        self.test_temp = Test()

    def get(self, test):
        apis = {
            "test_user_data": self.test.test_user_data,
            "test_userlogintime_data": self.test.test_userlogintime_data,
            "test_usercommission_data": self.test.test_usercommission_data,
            "test_products_data": self.testproduct.test_products_data
        }
        return apis

    def post(self, test):
        apis = {
            "auto_complete": self.test_temp.auto_complete_order,
        }
        return apis