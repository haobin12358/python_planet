# -*- coding:utf8 -*-

from datetime import datetime

from PIL import Image
import qrcode
import requests
from io import BytesIO


def make_qrcode(img_src, data_url, save_path):
    """
    :param img_src: 二维码中心图片
    :param data_url: 生成二维码的地址
    :param save_path: 二维码存储路径+文件名, 图片为.png格式
    :return:
    """
    qr = qrcode.QRCode(version=5, error_correction=qrcode.constants.ERROR_CORRECT_H, box_size=8, border=4)
    # qr.add_data("http://www.cnblogs.com/sfnz/")
    qr.add_data(data_url)
    qr.make(fit=True)

    img = qr.make_image()
    img = img.convert("RGBA")

    #logo="D:/favicon.jpg"
    # icon = Image.open("D:/132.jpg")

    # img_src = icon_url
    response = requests.get(img_src)
    icon = Image.open(BytesIO(response.content))
    # image.show()
    # icon = image
    img_w, img_h = img.size
    factor = 4
    size_w = int(img_w / factor)
    size_h = int(img_h / factor)

    icon_w, icon_h = icon.size
    if icon_w > size_w:
        icon_w = size_w
    if icon_h > size_h:
        icon_h = size_h
    icon = icon.resize((icon_w, icon_h), Image.ANTIALIAS)

    w = int((img_w - icon_w)/2)
    h = int((img_h - icon_h)/2)
    icon = icon.convert("RGBA")
    img.paste(icon, (w, h), icon)
    # img.show()
    # img.save('D:/createlogo.png')
    # qrcode_name = now_time + '.png'
    img.save(save_path)
    # return save_path