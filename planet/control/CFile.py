# -*- coding: utf-8 -*-
import os
from datetime import datetime

from flask import request, current_app

from planet.common.error_response import NotFound, ParamsError, SystemError
from planet.common.params_validates import parameter_required
from planet.common.success_response import Success
from planet.config.http_config import API_HOST


class CFile(object):
    def upload_img(self):
        file = request.files.get('file')
        data = parameter_required()
        folder = self.allowed_folder(data.get('type'))
        if not file:
            raise ParamsError(u'上传有误')
        filename = file.filename
        shuffix = os.path.splitext(filename)[-1]
        if self.allowed_file(shuffix):
            newName = self.new_name(shuffix)
            img_name = newName
            time_now = datetime.now()
            year = str(time_now.year)
            month = str(time_now.month)
            day = str(time_now.day)
            newPath = os.path.join(current_app.config['BASEDIR'], 'img', folder, year, month, day)
            if not os.path.isdir(newPath):
                os.makedirs(newPath)
            newFile = os.path.join(newPath, newName)
            file.save(newFile)  # 保存图片
            data = '/img/{}/{}/{}/{}/{}'.format(folder, year, month, day, img_name)
            # todo 是视频 增加缩略图
            # if shuffix in []
            return Success(u'上传成功', data)
        else:
            return SystemError(u'上传有误')

    def remove(self):
        data = parameter_required(('img_url', ))
        try:
            img_url = data.get('img_url')
            dirs = img_url.split('/')[-6:]
            name_shuffer = dirs[-1]
            name = name_shuffer.split('.')[0]
            if not name.endswith('anonymous') and not name.endswith(request.user.id):
                raise NotFound()
            path = os.path.join(current_app.config['BASEDIR'], '/'.join(dirs))
            os.remove(path)
        except Exception as e:
            raise NotFound()
        return Success(u'删除成功')

    @staticmethod
    def allowed_file(shuffix):
        return shuffix.lower() in ['.jpg', '.jpeg', '.png', '.gif', '.mp4', '.avi', '.wmv']

    @staticmethod
    def allowed_folder(folder):
        return folder if folder in ['index', 'product', 'temp', 'item', 'category', 'video'] else 'temp'

    @staticmethod
    def new_name(shuffix):
        import string, random  # import random
        myStr = string.ascii_letters + '12345678'
        try:
            usid = request.user.id
        except AttributeError as e:
            usid = 'anonymous'
        return ''.join(random.choice(myStr) for i in range(20)) + usid + shuffix

