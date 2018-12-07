# -*- coding:utf8 -*-

from datetime import datetime

from PIL import Image
import qrcode


def qrcodeWithurl(url, savepath):
    """
    生成url二维码
    :param url:
    :param savepath: 保存路径
    :return:
    """
    img=qrcode.make(url)
    # savepath='1.png'
    img.save(savepath)


def qrcodeWithtext(text, savepath):
    """
    生成文本二维码
    :param text:
    :return:
    """
    img=qrcode.make(text)
    #保存图片
    # savepath='2.png'
    img.save(savepath)


def qrcodeWithlogo(url, logo_file, savepath):
    """
    生成带logo的二维码
    :param url:
    :param logo_file:
    :param savepath:
    :return:
    """
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.ERROR_CORRECT_H,
        box_size=10,
        border=4,
    )
    qr.add_data(url)
    qr.make(fit=True)

    img = qr.make_image()
    # 设置二维码为彩色
    img = img.convert("RGBA")
    icon = Image.open(logo_file)
    w, h = img.size
    factor = 4
    size_w = int(w / factor)
    size_h = int(h / factor)
    icon_w, icon_h = icon.size
    if icon_w > size_w:
        icon_w = size_w
    if icon_h > size_h:
        icon_h = size_h
    icon = icon.resize((icon_w, icon_h), Image.ANTIALIAS)
    w = int((w - icon_w) / 2)
    h = int((h - icon_h) / 2)
    icon = icon.convert("RGBA")
    newimg = Image.new("RGBA", (icon_w + 8, icon_h + 8), (255, 255, 255))
    img.paste(newimg, (w - 4, h - 4), newimg)

    img.paste(icon, (w, h), icon)
    img.save(savepath, quality=100)
