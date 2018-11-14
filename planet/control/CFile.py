# -*- coding: utf-8 -*-
import os
from datetime import datetime
from flask import request, current_app

from planet.common.error_response import NotFound, ParamsError, SystemError
from planet.common.params_validates import parameter_required
from planet.common.success_response import Success
from planet.common.token_handler import token_required
from planet.common.video_extraction_thumbnail import video2frames
from planet.config.http_config import API_HOST


class CFile(object):
    @token_required
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
            if shuffix in ['.mp4', '.avi', '.wmv']:
                upload_type = 'video'
                # 生成视频缩略图
                thum_origin_name = img_name.split('.')[0]
                thum_name = video2frames(newFile, newPath, output_prefix=thum_origin_name,
                                         extract_time_points=(2,), jpg_quality=80)
                video_thum = '/img/{}/{}/{}/{}/{}'.format(folder, year, month, day, thum_name.get('thumbnail_name_list')[0])
                dur_second = int(thum_name.get('video_duration', 0))
                minute = dur_second // 60
                second = dur_second % 60
                minute_str = '0' + str(minute) if minute < 10 else str(minute)
                second_str = '0' + str(second) if second < 10 else str(second)
                video_dur = minute_str + ':' + second_str
            else:
                upload_type = 'image'
                video_thum = ''
                video_dur = ''
            return Success(u'上传成功', data).get_body(video_thum=video_thum, upload_type=upload_type,
                                                   video_dur=video_dur)
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

