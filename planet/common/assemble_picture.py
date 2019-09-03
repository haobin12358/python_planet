import os
import uuid
from datetime import datetime

import requests
from flask import current_app

from planet.common import make_qrcode
from PIL import Image as img
from PIL import ImageFont as imf
from PIL import ImageDraw as imd

from planet.config.http_config import MEDIA_HOST
from planet.extensions.tasks import contenttype_config
# import numpy as np

class AssemblePicture():

    def __init__(self, *args, **kwargs):
        if kwargs:
            self.prmain = kwargs.get('prmain')
            self.prtitle = kwargs.get('prtitle')
            self.prid = kwargs.get('prid')
            self.prprice = kwargs.get('prprice')
            self.prlineprice = kwargs.get('prlineprice')

        elif args:
            self.prid = args[0]
            self.prtitle = args[1]
            self.prprice = args[2]
            self.prlineprice = args[3]
            self.prmain = args[4]

        # self.res_path = r"..\extensions\staticres"
        self.res_path = os.path.join(current_app.config['BASEDIR'], 'planet','extensions', 'staticres')

        current_app.logger.info(
            'start assemble product prid {} prmain {} prtitle {} prprice {}  prlineprice {}'.format(
                self.prid, self.prmain, self.prtitle, self.prprice, self.prlineprice
            ))
        # print(
        #     'start assemble product prid {} prmain {} prtitle {} prprice {}  prlineprice {}'.format(
        #         self.prid, self.prmain, self.prtitle, self.prprice, self.prlineprice
        #     ))
        if not self.prlineprice:
            self.prlineprice = self.prprice

        if not (self.prid and self.prlineprice and self.prmain and self.prtitle and self.prlineprice):
            raise Exception('参数不齐')
        if len(self.prtitle) >= 32:
            self.prtitle = str(self.prtitle[:29]) + '...'

    def _get_path(self, fold):
        """获取服务器上文件路径"""
        time_now = datetime.now()
        year = str(time_now.year)
        month = str(time_now.month)
        day = str(time_now.day)
        filepath = os.path.join(current_app.config['BASEDIR'], 'img', fold, year, month, day)
        file_db_path = os.path.join('/img', fold, year, month, day)
        if not os.path.isdir(filepath):
            os.makedirs(filepath)
        return filepath, file_db_path

    def _get_fetch(self, qiniu=False):
        if qiniu:
            content = requests.get(MEDIA_HOST + self.prmain)
        else:
            content = requests.get(self.prmain)
        url_type = contenttype_config.get(content.headers._store.get('content-type')[-1])
        current_app.logger.info('get url type = {}'.format(url_type))
        if not url_type:
            current_app.logger.info('当前url {} 获取失败 或url 不是图片格式'.format(self.prmain))
            return
        filename = str(uuid.uuid1()) + url_type

        filepath, filedbpath = self._get_path('backup')
        filedbname = os.path.join(filedbpath, filename)
        filename = os.path.join(filepath, filename)
        with open(filename, 'wb') as head:
            head.write(content.content)
        self.prmain = filedbname

    def assemble(self):
        # current_app.logger.info('current config basedir : {}'.format(current_app.config['BASEDIR']))
        current_app.logger.info('prmain = {}'.format(os.path.join(current_app.config['BASEDIR'], self.prmain[1:])))
        if not str(self.prmain).startswith('/img'):
            if not (str(self.prmain).startswith('http') or str(self.prmain).startswith('https')):
                return
            else:
                self._get_fetch()
        else:
            if not os.path.isfile(self.prmain):
                self._get_fetch(qiniu=True)

        prmain = img.open(os.path.join(current_app.config['BASEDIR'], self.prmain[1:]))
        if not str(self.prmain).endswith('png'):
            # prmain.save(self.res_path + r'\prmain.png')
            prmain.save(os.path.join(self.res_path, 'prmain.png'))
            # prmain = img.open(self.res_path + r'\prmain.png')
            prmain = img.open(os.path.join(self.res_path, 'prmain.png'))
        # prmain.resize((750, 750), img.ANTIALIAS)
        prmain.thumbnail((750, 750))
        # item_img = img.open(self.res_path + r'\item.png')
        item_img = img.open(os.path.join(self.res_path, 'item.png'))
        item_img.thumbnail((394, 25))
        new_im = img.new('RGBA', (750, 1000), color='white')
        x, y = prmain.size
        if max(x, y) < 750:
            new_im.paste(prmain, ((750 - x) // 2, (750 - y) // 2))
        else:
            new_im.paste(prmain, (0, 0))
        # 商品标题
        # prtitle_font = imf.truetype(self.res_path + r'\PingFang Medium_downcc.otf', 28)
        prtitle_font = imf.truetype(os.path.join(self.res_path, 'PingFang Medium_downcc.otf'), 28)
        draw = imd.Draw(new_im)
        text_prtitle_list = []
        for index, end_limit in enumerate(range(0, len(self.prtitle), 16)):
            text_prtitle_list.append(self.prtitle[index * 16: end_limit + 16])
        print(text_prtitle_list)
        draw.text((31, 801), '\n'.join(text_prtitle_list), fill="#333333", font=prtitle_font)

        # 商品价格
        # prprice_font = imf.truetype(self.res_path + r'\PingFang SC Semibold.ttf', 36)
        prprice_font = imf.truetype(os.path.join(self.res_path, 'PingFang SC Semibold.ttf'), 36)
        # icon_font = imf.truetype(self.res_path + r'\PingFang Regular.otf', 24)
        icon_font = imf.truetype(os.path.join(self.res_path, 'PingFang Regular.otf'), 24)
        draw.text((31, 903), str('￥'), fill='#E56C2F', font=icon_font)
        draw.text((50, 891), str('%.2f' % self.prprice), fill='#E56C2F', font=prprice_font)
        # 划线价格
        # lineprice_font = imf.truetype(self.res_path + r'\PingFang Light.ttf', 20)
        lineprice_font = imf.truetype(os.path.join(self.res_path, 'PingFang Light.ttf'), 20)
        draw.text((209, 908), str('￥ %.2f' % self.prlineprice), fill='#999999', font=lineprice_font)
        # 中划线
        draw.line((210, 925, 323, 925), fill='#999999', width=1)

        # 插入标签图片
        new_im.paste(item_img, (31, 951))
        # new_im.show()
        time_now = datetime.now()
        year = str(time_now.year)
        month = str(time_now.month)
        day = str(time_now.day)
        folder = 'base'
        newPath = os.path.join(current_app.config['BASEDIR'], 'img', folder, year, month, day)
        if not os.path.isdir(newPath):
            os.makedirs(newPath)
        img_name = '{}{}.png'.format(time_now.timestamp(), self.prid)

        newFile = os.path.join(newPath, img_name)

        data = '/img/{folder}/{year}/{month}/{day}/{img_name}'.format(
            folder=folder, year=year, month=month, day=day, img_name=img_name)

        new_im.save(newFile)
        # new_im.save(r'C:\Users\刘帅斌\Desktop\assemble.png')
        # todo  商品上架增加该图片的合成接口

        return data

    def add_qrcode(self, url, assemble_path):

        base = img.open(os.path.join(current_app.config['BASEDIR'], assemble_path[1:]))
        # logo = self.res_path + r'\logo.png'
        logo = os.path.join(self.res_path, 'logo.png')
        time_now = datetime.now()
        year = str(time_now.year)
        month = str(time_now.month)
        day = str(time_now.day)
        folder = 'qrcode'
        folder_promotion = 'promotion'

        newPath = os.path.join(current_app.config['BASEDIR'], 'img', folder, year, month, day)
        if not os.path.isdir(newPath):
            os.makedirs(newPath)
        img_name = '{}{}.png'.format(time_now.timestamp(), self.prid)

        newFile = os.path.join(newPath, img_name)

        # data = '/img/{folder}/{year}/{month}/{day}/{img_name}'.format(
        #     folder=folder, year=year, month=month, day=day, img_name=img_name)
        # newFile =
        make_qrcode.qrcodeWithlogo(url, logo, newFile)
        qrcode = img.open(newFile)
        qrcode.thumbnail((172, 172))
        base.paste(qrcode, (540, 801))
        # 商品价格
        # prprice_font = imf.truetype(self.res_path + r'\PingFang SC Semibold.ttf', 36)
        prprice_font = imf.truetype(os.path.join(self.res_path, 'PingFang SC Semibold.ttf'), 36)
        # icon_font = imf.truetype(self.res_path + r'\PingFang Regular.otf', 24)
        icon_font = imf.truetype(os.path.join(self.res_path, 'PingFang Regular.otf'), 24)
        draw = imd.Draw(base)
        draw.rectangle((31, 891, 200, 940), fill=(255, 255, 255))
        draw.text((31, 903), str('￥'), fill='#E56C2F', font=icon_font)
        draw.text((50, 891), str('%.2f' % self.prprice), fill='#E56C2F', font=prprice_font)
        promotion_path = os.path.join(current_app.config['BASEDIR'], 'img', folder_promotion, year, month, day)
        if not os.path.isdir(promotion_path):
            os.makedirs(promotion_path)

        promotion_name = '{}{}.png'.format(time_now.timestamp(), self.prid)
        data = '/img/{folder}/{year}/{month}/{day}/{img_name}'.format(
                folder=folder_promotion, year=year, month=month, day=day, img_name=promotion_name)

        local_path = os.path.join(promotion_path, promotion_name)
        base.save(local_path)
        current_app.logger.info('get promotion url ： {}'.format(local_path))
        return data, local_path


if __name__ == '__main__':
    # prmain = r'C:\Users\刘帅斌\Desktop\test.jpg'
    # prmain = r'C:\Users\刘帅斌\Desktop\deno.png'
    # prtitle = '这是一个很酷的商品' * 5
    # prprice = 120.10
    # prlineprice = 155.00
    # prid = 'testprid'
    # a = AssemblePicture(prid, prtitle, prprice, prlineprice, prmain)
    # a.assemble()
    # a.add_qrcode('')
    pass
