# -*- coding: utf-8 -*-
from planet.control.CSetSupper import CSetSupper
from planet.common.base_resource import Resource


class ASetSupper(Resource):

    def __init__(self):
        self.setsupper = CSetSupper()

    def post(self, setsupper):
        apis ={
            'test':self.setsupper.test
        }
        return apis
