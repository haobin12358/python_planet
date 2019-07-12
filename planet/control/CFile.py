# -*- coding: utf-8 -*-
import os
from datetime import datetime
from flask import request, current_app

from PIL import Image

from planet.common.compress_picture import CompressPicture
from planet.common.error_response import NotFound, ParamsError, SystemError
from planet.common.params_validates import parameter_required
from planet.common.success_response import Success
from planet.common.token_handler import token_required, is_tourist
from planet.common.video_extraction_thumbnail import video2frames
from planet.config.http_config import API_HOST
from planet.extensions.qiniu.storage import QiniuStorage


class CFile(object):
    def __init__(self):
        self.qiniu = QiniuStorage(current_app)
        self.upload_to_qiniu = ('https://www.bigxingxing.com', 'https://pre2.bigxingxing.com')

    # @token_required
    def upload_img(self):
        if is_tourist():
            current_app.logger.info(">>>  Tourist Uploading Files  <<<")
        else:
            current_app.logger.info(">>>  {} Uploading Files  <<<".format(request.user.model))
        self.check_file_size()
        file = request.files.get('file')
        data = parameter_required()
        if not data:
            data = request.form
            current_app.logger.info('form : {}'.format(data))
        current_app.logger.info('type is {}'.format(data.get('type')))
        folder = self.allowed_folder(data.get('type'))
        if not file:
            raise ParamsError(u'上传有误')
        file_data = self._upload_file(file, folder)
        return Success('上传成功', data=file_data[0]).get_body(video_thum=file_data[1], video_dur=file_data[2], upload_type=file_data[3])

    # @token_required
    def batch_upload(self):
        if is_tourist():
            current_app.logger.info(">>>  Tourist Bulk Uploading Files  <<<")
        else:
            current_app.logger.info(">>>  {} Bulk Uploading Files  <<<".format(request.user.model))
        self.check_file_size()
        files = request.files.to_dict()
        current_app.logger.info(">>> Uploading {} Files  <<<".format(len(files)))
        if len(files) > 30:
            raise ParamsError('最多可同时上传30张图片')
        # todo 视频数量限制
        data = parameter_required()
        folder = self.allowed_folder(data.get('type'))
        file_url_list = []
        for file in files.values():
            upload_file = self._upload_file(file, folder)
            file_dict = {
                'data': upload_file[0],
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
            if shuffix in ['.mp4', '.avi', '.wmv', '.mov', '.3gp', '.flv', '.mpg']:
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

                if API_HOST in self.upload_to_qiniu:
                    try:
                        self.qiniu.save(data=newFile, filename=data[1:])
                    except Exception as e:
                        current_app.logger.error(">>>  视频上传到七牛云出错 : {}  <<<".format(e))
                        raise ParamsError('上传视频失败，请稍后再试')

                video_thumbnail_path = os.path.join(newPath, thum_name.get('thumbnail_name_list')[0])

                if API_HOST in self.upload_to_qiniu:
                    try:
                        self.qiniu.save(data=video_thumbnail_path, filename=video_thum[1:])
                    except Exception as e:
                        current_app.logger.error(">>>  视频预览图上传到七牛云出错 : {}  <<<".format(e))
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
                try:
                    thumbnail_img = CompressPicture().resize_img(ori_img=newFile, ratio=0.8, save_q=80)
                except Exception as e:
                    current_app.logger.info(">>>  Resize Picture Error : {}  <<<".format(e))
                    raise ParamsError('图片格式错误，请检查后重新上传（请勿强制更改图片后缀名）')
                data += '_' + thumbnail_img.split('_')[-1]
                # 上传到七牛云，并删除本地压缩图

                if API_HOST in self.upload_to_qiniu:
                    try:
                        self.qiniu.save(data=thumbnail_img, filename=data[1:])
                        os.remove(str(newFile + '_' + thumbnail_img.split('_')[-1]))
                    except Exception as e:
                        current_app.logger.error(">>>  图片上传到七牛云出错 : {}  <<<".format(e))
                        raise ParamsError('上传图片失败，请稍后再试')
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
        max_file_size = 50 * 1024 * 1024
        upload_file_size = request.content_length
        current_app.logger.info(">>>  Upload File Size is {0} MB <<<".format(round(upload_file_size/1048576, 2)))
        if upload_file_size > max_file_size:
            raise ParamsError("上传文件过大，请上传小于50MB的文件")

    @staticmethod
    def allowed_file(shuffix):
        return shuffix in ['.jpg', '.jpeg', '.png', '.gif', '.mp4', '.avi', '.wmv', '.mov', '.3gp', '.flv', '.mpg']

    @staticmethod
    def allowed_folder(folder):
        return folder if folder in ['index', 'product', 'temp', 'item', 'news', 'category', 'video', 'avatar',
                                    'voucher', 'idcard', 'brand', 'activity', 'contract', 'play',
                                    'scenicspot', 'raiders', 'travels', 'essay'] else 'temp'

    def new_name(self, shuffix):
        import string
        import random
        myStr = string.ascii_letters + '12345678'
        try:
            if hasattr(request, 'user'):
                usid = request.user.id
            else:
                from itsdangerous import TimedJSONWebSignatureSerializer as Serializer
                s = Serializer(current_app.config['SECRET_KEY'])
                token = request.form.get('token')
                user = s.loads(token)
                usid = user.get('id')
        except Exception as e:
            current_app.logger.error('Error is {}'.format(e))
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

    def pull_url_to_storage(self):
        """一次性的测试方法，忽略就好"""
        data = request.json
        url_list = data.get('url_list')
        rets = []
        for url in url_list:
            # ret, info = self.qiniu.url_to_storage('https://www.bigxingxing.com' + url, url[1:])
            ret, info = self.qiniu.save('/opt/planet_version2' + url, url[1:])
            rets.append(ret)
        # current_app.logger.info(rets)
        current_app.logger.info(len(rets))
        return Success('成功')

