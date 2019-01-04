# -*- coding: utf-8 -*-
import os
from datetime import datetime
from flask import request, current_app

from PIL import Image

from planet.common.compress_picture import CompressPicture
from planet.common.error_response import NotFound, ParamsError, SystemError
from planet.common.params_validates import parameter_required
from planet.common.success_response import Success
from planet.common.token_handler import token_required
from planet.common.video_extraction_thumbnail import video2frames
from planet.config.http_config import API_HOST


class CFile(object):
    @token_required
    def upload_img(self):
        self.check_file_size()
        file = request.files.get('file')
        data = parameter_required()
        folder = self.allowed_folder(data.get('type'))
        if not file:
            raise ParamsError(u'上传有误')
        file_data = self._upload_file(file, folder)
        return Success('上传成功', data=file_data[0]).get_body(video_thum=file_data[1], video_dur=file_data[2], upload_type=file_data[3])

    @token_required
    def batch_upload(self):
        self.check_file_size()
        files = request.files.to_dict()
        if len(files) > 9:
            raise ParamsError('最多可同时上传9张图片')
        # todo 视频数量限制
        data = parameter_required()
        folder = self.allowed_folder(data.get('type'))
        file_url_list = []
        for file in files.values():
            upload_file = self._upload_file(file, folder)
            file_dict = {
                'file_url': upload_file[0],
                'video_thum': upload_file[1],
                'video_dur': upload_file[2],
                'upload_type': upload_file[3]
            }
            file_url_list.append(file_dict)
        return Success('上传成功', file_url_list)

    def _upload_file(self, file, folder):
        filename = file.filename
        shuffix = os.path.splitext(filename)[-1]
        current_app.logger.info(">>>  Upload File Shuffix is {0}  <<<".format(shuffix))
        shuffix = shuffix.lower()
        if self.allowed_file(shuffix):
            img_name = self.new_name(shuffix)
            time_now = datetime.now()
            year = str(time_now.year)
            month = str(time_now.month)
            day = str(time_now.day)
            newPath = os.path.join(current_app.config['BASEDIR'], 'img', folder, year, month, day)
            if not os.path.isdir(newPath):
                os.makedirs(newPath)
            newFile = os.path.join(newPath, img_name)
            file.save(newFile)  # 保存图片
            data = '/img/{folder}/{year}/{month}/{day}/{img_name}'.format(folder=folder, year=year,
                                                                          month=month, day=day,
                                                                          img_name=img_name)
            if shuffix in ['.mp4', '.avi', '.wmv', '.mov', '3gp', 'flv', 'mpg']:
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

                # 读取
                # img = Image.open(thumbnail_img)
                # img_size = '_' + 'x'.join(map(str, img.size))
                # path_with_size = thumbnail_img + img_size + shuffix
                # data += (img_size + shuffix)
                # img.save(path_with_size)
                # os.remove(newFile)

                # 生成压缩图
                thumbnail_img = CompressPicture.resize_img(ori_img=newFile, ratio=0.5, save_q=45)
                data += '_' + thumbnail_img.split('_')[-1]
            current_app.logger.info(">>>  Upload File Path is  {}  <<<".format(data))
            return data, video_thum, video_dur, upload_type
        else:
            raise SystemError(u'上传有误, 不支持的文件类型 {}'.format(shuffix))

    def remove(self):
        data = parameter_required(('img_url', ))
        try:
            img_url = data.get('img_url')
            dirs = img_url.split('/')[-6:]
            name_shuffer = dirs[-1]
            name = name_shuffer.split('.')[0]
            if not 'anonymous' in name and request.user.id not in name:
                raise NotFound()
            path = os.path.join(current_app.config['BASEDIR'], '/'.join(dirs))
            os.remove(path)
        except Exception as e:
            raise NotFound()
        return Success(u'删除成功')

    def check_file_size(self):
        max_file_size = 20 * 1024 * 1024
        upload_file_size = request.content_length
        current_app.logger.info(">>>  Upload File Size is {0} MB <<<".format(round(upload_file_size/1048576, 2)))
        if upload_file_size > max_file_size:
            raise ParamsError("上传文件过大，请上传小于20MB的文件")

    @staticmethod
    def allowed_file(shuffix):
        return shuffix in ['.jpg', '.jpeg', '.png', '.gif', '.mp4', '.avi', '.wmv', '.mov', '3gp', 'flv', 'mpg']

    @staticmethod
    def allowed_folder(folder):
        return folder if folder in ['index', 'product', 'temp', 'item', 'news', 'category', 'video', 'avatar',
                                    'voucher', 'idcard', 'brand', 'activity'] else 'temp'

    def new_name(self, shuffix):
        import string, random  # import random
        myStr = string.ascii_letters + '12345678'
        try:
            usid = request.user.id
        except AttributeError as e:
            usid = 'anonymous'
        res = ''.join(random.choice(myStr) for _ in range(20)) + usid + shuffix
        return res

    @staticmethod
    def get_img_size(file):
        try:
            img = Image.open(file)
            return '_' + 'x'.join(map(str, img.size))
        except Exception as e:
            return ''

