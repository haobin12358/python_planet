# -*- coding: utf-8 -*-
from planet.common.base_resource import Resource
from planet.control.CFile import CFile


class AFile(Resource):
    def __init__(self):
        self.cfile = CFile()

    def post(self, file):
        apis = {
            'upload': self.cfile.upload_img,
            'remove': self.cfile.remove,
        }
        return apis
