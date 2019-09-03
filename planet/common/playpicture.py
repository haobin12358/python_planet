import os
import uuid
from datetime import datetime

import requests
from flask import current_app

from planet.common import make_qrcode
from PIL import Image as img, ImageFilter
from PIL import ImageFont as imf
from PIL import ImageDraw as imd

from planet.config.http_config import MEDIA_HOST
from planet.extensions.tasks import contenttype_config


class MyGaussianBlur(ImageFilter.Filter):
    name = "GaussianBlur"

    def __init__(self, radius=2, bounds=None):
        self.radius = radius
        self.bounds = bounds

    def filter(self, image):
        if self.bounds:
            clips = image.crop(self.bounds).gaussian_blur(self.radius)
            image.paste(clips, self.bounds)
            return image
        else:
            return image.gaussian_blur(self.radius)


class PlayPicture():
    # res_path = '../extensions/staticres/'
    def __init__(self):
        self.res_path = os.path.join(current_app.config['BASEDIR'], 'planet', 'extensions', 'staticres')
        self.pro_1 = '跟旗行一起游山玩水'
        self.pro_2 = '长按扫码加入我们'
        self.temp_path = ''

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

    def _get_fetch(self, path, qiniu=False):
        if qiniu:
            content = requests.get(MEDIA_HOST + path)
        else:
            content = requests.get(path)
        url_type = contenttype_config.get(content.headers._store.get('content-type')[-1])
        current_app.logger.info('get url type = {}'.format(url_type))
        if not url_type:
            current_app.logger.info('当前url {} 获取失败 或url 不是图片格式'.format(path))
            return
        filename = str(uuid.uuid1()) + url_type

        filepath, filedbpath = self._get_path('backup')
        filedbname = os.path.join(filedbpath, filename)
        filename = os.path.join(filepath, filename)
        with open(filename, 'wb') as head:
            head.write(content.content)
        return filedbname

    def create(self, path, plname, starttime, endtime, playprice, usid, plid, wxacode):
        if not str(path).startswith('/img'):
            if not (str(path).startswith('http') or str(path).startswith('https')):
                return
            else:
                current_app.logger.info('当前图片路由{} 不在当前服务，需拉取资源'.format(path))
                path = self._get_fetch(path)
        else:
            # path =

            if not os.path.isfile(os.path.join(current_app.config['BASEDIR'], path[1:])):
                current_app.logger.info('当前图片路由{} 不在当前服务，需从图片服务器拉取资源'.format(path))
                path = self._get_fetch(path, qiniu=True)

        # new_im = img.new('RGBA', (750, 1010), color='white')
        if len(plname) >= 34:
            plname = plname[:30] + '..'
        # current_app.logger.info('get playprice = {} len = {}'.format(playprice, len(playprice)))
        if len(playprice) >= 6:
            playprice = playprice.split('.')[0]
        current_app.logger.info('get after playprice = {} len = {}'.format(playprice, len(playprice)))

        local_path = os.path.join(current_app.config['BASEDIR'], path[1:])
        new_im = img.open(local_path)
        shuffix = str(path).split('.')[-1]
        x, y = new_im.size
        if x != 750 or y != 1010:
            temp_path = os.path.join(self._get_path('tmp')[0], 'temp{}.{}'.format(str(uuid.uuid1()), shuffix))
            new_im.resize((750, 1010), img.LANCZOS).save(temp_path)
            new_im = img.open(temp_path)
        # 模糊处理
        new_im = new_im.filter(MyGaussianBlur(radius=30))
        dw = imd.Draw(new_im)
        # 蒙版
        black = img.new('RGBA', (750, 1010), color=(0, 0, 0, 60))
        dw.bitmap((0, 0), black, fill=(0, 0, 0, 50))
        # 大矩形
        # self.drawRoundRec(new_im, 'white', 35, 50, 680, 680, 60)
        self.drawrec(dw, 'white', 35, 46, 680, 680)
        # 内容图片
        inner_im = img.open(local_path)
        if x != 640 or y != 374:
            temp_path = os.path.join(self._get_path('tmp')[0], 'temp2{}.{}'.format(str(uuid.uuid1()), shuffix))

            inner_im.resize((640, 374), img.LANCZOS).save(temp_path)
            inner_im = img.open(temp_path)
        new_im.paste(inner_im, (55, 90))

        # 活动内容
        plnamefont = imf.truetype(os.path.join(self.res_path, 'PingFang Medium_downcc.otf'), 40)
        plnamelist = []
        for index, end_limit in enumerate(range(0, len(plname), 16)):
            plnamelist.append(plname[index * 16: end_limit + 16])

        dw.text((55, 490), '\n'.join(plnamelist), font=plnamefont, fill='#000000')
        # 出发时间
        timefont = imf.truetype(os.path.join(self.res_path, 'PingFang Regular.otf'), 30)
        dw.text((55, 632), '出游时间: {}-{}'.format(
            starttime, endtime), font=timefont, fill='#000000')
        # ￥
        icon_font = imf.truetype(os.path.join(self.res_path, 'PingFang Regular.otf'), 48)

        # 小矩形
        h_ = (len(str(playprice)) + 2) * 26
        x_ = 683 - h_
        self.drawrec(dw, '#FFCE00', x_ + 2, 643, h_ + 13, 34)

        dw.text((x_, 610), '￥', font=icon_font, fill='#000000')

        # 价格
        pricefont = imf.truetype(os.path.join(self.res_path, 'PingFang SC Semibold.ttf'), 60)
        price_x = 670 - len(str(playprice) * 26)
        dw.text((price_x, 600), playprice, font=pricefont, fill='#000000')

        # pro1
        profont_1 = imf.truetype(os.path.join(self.res_path, 'PangMenZhengDao.ttf'), 52)
        dw.text((47, 831), self.pro_1, font=profont_1, fill='#FFFFFF')
        # pro2
        profont_2 = imf.truetype(os.path.join(self.res_path, 'PingFangSCRegular.ttf'), 32)
        dw.text((47, 875), self.pro_2, font=profont_2, fill='#FFFFFF')
        # 小程序码底层矩形
        # self.draw_round_rec(dw, 'white', 555, 789, 160, 160, 40)
        # 小程序码
        wxacode = img.open(os.path.join(current_app.config['BASEDIR'], wxacode[1:]))
        temp_path = os.path.join(self._get_path('tmp')[0], 'temp3{}.{}'.format(str(uuid.uuid1()), shuffix))
        wxacode.resize((160, 160), img.LANCZOS).save(temp_path)
        wxacode = img.open(temp_path)
        new_im.paste(wxacode, (555, 789))
        # new_im.show()
        new_im_path, new_im_db_path = self._get_path('play')
        random_num = datetime.now().timestamp()
        db_path = os.path.join(new_im_db_path, 'promotion{}{}{}.{}'.format(plid, usid, random_num, shuffix))
        local_path = os.path.join(new_im_path, 'promotion{}{}{}.{}'.format(plid, usid, random_num, shuffix))
        # db_path = os.path.join(new_im_db_path, 'promotion{}{}.{}'.format(plid, usid, shuffix))
        # local_path = os.path.join(new_im_path, 'promotion{}{}.{}'.format(plid, usid, shuffix))

        new_im.save(local_path)
        return local_path, db_path

    def draw_round_rec(self, dw, color, x, y, w, h, r):
        """
        绘制圆角矩形
        :param dw: 绘制对象
        :param color: 背景颜色
        :param x: 起始坐标
        :param y: 起始坐标
        :param w: 宽度
        :param h: 高度
        :param r: 圆角
        :return:
        """

        # im = img.open(imgPath)
        # dw = imd.Draw(im)

        '''Rounds'''
        dw.ellipse((x, y, x + r, y + r), fill=color)
        dw.ellipse((x + w - r, y, x + w, y + r), fill=color)
        dw.ellipse((x, y + h - r, x + r, y + h), fill=color)
        dw.ellipse((x + w - r, y + h - r, x + w, y + h), fill=color)

        '''rec.s'''
        dw.rectangle((x + r / 2, y, x + w - r / 2, y + h), fill=color)
        dw.rectangle((x, y + r / 2, x + w, y + h - r / 2), fill=color)

    def drawrec(self, dw, color, x, y, w, h, r=0):
        """
        绘制矩形
        :param dw:
        :param color:
        :param x:
        :param y:
        :param w:
        :param h:
        :return:
        """
        if r:
            # 绘制圆角
            return self.draw_round_rec(dw, color, x, y, w, h, r)
        # dw = imd.Draw(im)
        dw.rectangle((x, y, x + w, y + h), fill=color)

    def create_ticket(self, path, tiname, starttime, endtime, playprice, usid, tiid, wxacode):
        if not str(path).startswith('/img'):
            if not (str(path).startswith('http') or str(path).startswith('https')):
                return
            else:
                current_app.logger.info('当前图片路由{} 不在当前服务，需拉取资源'.format(path))
                path = self._get_fetch(path)
        else:
            # path =

            if not os.path.isfile(os.path.join(current_app.config['BASEDIR'], path[1:])):
                current_app.logger.info('当前图片路由{} 不在当前服务，需从图片服务器拉取资源'.format(path))
                path = self._get_fetch(path, qiniu=True)

        # new_im = img.new('RGBA', (750, 1010), color='white')
        if len(tiname) >= 34:
            tiname = tiname[:30] + '..'

        if len(playprice) >= 6:
            playprice = playprice.split('.')[0]
        current_app.logger.info('get after playprice = {} len = {}'.format(playprice, len(playprice)))

        local_path = os.path.join(current_app.config['BASEDIR'], path[1:])
        new_im = img.open(local_path)
        shuffix = str(path).split('.')[-1]
        x, y = new_im.size
        if x != 750 or y != 1270:
            temp_path = os.path.join(self._get_path('tmp')[0], 'temp{}.{}'.format(str(uuid.uuid1()), shuffix))
            new_im.resize((750, 1270), img.LANCZOS).save(temp_path)
            new_im = img.open(temp_path)
        # 模糊处理
        new_im = new_im.filter(MyGaussianBlur(radius=30))
        dw = imd.Draw(new_im)
        # 蒙版
        black = img.new('RGBA', (750, 1270), color=(0, 0, 0, 60))
        dw.bitmap((0, 0), black, fill=(0, 0, 0, 50))
        # 大矩形
        # self.drawRoundRec(new_im, 'white', 35, 50, 680, 680, 60)
        self.drawrec(dw, 'white', 35, 50, 680, 940)
        # 内容图片
        inner_im = img.open(local_path)
        if x != 640 or y != 640:
            temp_path = os.path.join(self._get_path('tmp')[0], 'temp2{}.{}'.format(str(uuid.uuid1()), shuffix))

            inner_im.resize((640, 640), img.LANCZOS).save(temp_path)
            inner_im = img.open(temp_path)

        new_im.paste(inner_im, (55, 90))

        # 门票信息
        tinamefont = imf.truetype(os.path.join(self.res_path, 'PingFang Medium_downcc.otf'), 40)
        tinamelist = []
        for index, end_limit in enumerate(range(0, len(tiname), 16)):
            tinamelist.append(tiname[index * 16: end_limit + 16])

        dw.text((55, 760), '\n'.join(tinamelist), font=tinamefont, fill='#000000')
        # TODO 出游时间字段未定
        # 出发时间
        timefont = imf.truetype(os.path.join(self.res_path, 'PingFang Regular.otf'), 30)
        dw.text((55, 902), '出游时间: {}-{}'.format(starttime, endtime), font=timefont, fill='#000000')
        # ￥
        icon_font = imf.truetype(os.path.join(self.res_path, 'PingFang Regular.otf'), 48)

        # 小矩形
        h_ = (len(str(playprice)) + 2) * 26
        x_ = 683 - h_
        self.drawrec(dw, '#FFCE00', x_ + 2, 913, h_ + 13, 34)

        dw.text((x_, 884), '￥', font=icon_font, fill='#000000')

        # 价格
        pricefont = imf.truetype(os.path.join(self.res_path, 'PingFang SC Semibold.ttf'), 60)
        price_x = 670 - len(str(playprice) * 26)
        dw.text((price_x, 874), playprice, font=pricefont, fill='#000000')

        # pro1
        profont_1 = imf.truetype(os.path.join(self.res_path, 'PangMenZhengDao.ttf'), 52)
        dw.text((47, 1077), self.pro_1, font=profont_1, fill='#FFFFFF')
        # pro2
        profont_2 = imf.truetype(os.path.join(self.res_path, 'PingFangSCRegular.ttf'), 32)
        dw.text((47, 1139), self.pro_2, font=profont_2, fill='#FFFFFF')
        # 小程序码底层矩形
        # self.draw_round_rec(dw, 'white', 555, 789, 160, 160, 40)
        # 小程序码
        wxacode = img.open(os.path.join(current_app.config['BASEDIR'], wxacode[1:]))
        temp_path = os.path.join(self._get_path('tmp')[0], 'temp3{}.{}'.format(str(uuid.uuid1()), shuffix))
        wxacode.resize((160, 160), img.LANCZOS).save(temp_path)
        wxacode = img.open(temp_path)
        new_im.paste(wxacode, (555, 1050))
        # new_im.show()
        new_im_path, new_im_db_path = self._get_path('play')
        random_num = datetime.now().timestamp()
        db_path = os.path.join(new_im_db_path, 'promotion{}{}{}.{}'.format(tiid, usid, random_num, shuffix))
        local_path = os.path.join(new_im_path, 'promotion{}{}{}.{}'.format(tiid, usid, random_num, shuffix))
        new_im.save(local_path)
        return local_path, db_path


if __name__ == '__main__':
    # path = r'D:\teamsystem\image\dxx-other\logo.png'
    path = r'E:\liushuaibin\image\test.jpg'
    tiname = '杭州富阳野生动物园门票 1张 杭州富阳野生动物园门票1张'
    # plame = '呼和浩特-希拉穆仁-响沙湾-达拉特旗-康巴什市区-成吉思汗陵-鄂尔多斯-公主府-蒙亮-大召寺·五日'
    starttime = '2019/6/10'
    endtime = '6/12'
    playprice = '1.56'
    # pp = PlayPicture().create_ticket(path, plame, starttime, endtime, playprice)
