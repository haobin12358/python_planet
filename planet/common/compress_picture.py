# coding:utf-8
from PIL import Image as image
# import Image as image


class CompressPicture(object):

    # 等比例压缩图片
    @staticmethod
    def resize_img(**args):
        """
        :param args: {ori_img:源图片, dst_img：目标图片,
                      dst_w：目标图片大小, dst_h:目标图片大小,
                      ratio:目标图片尺寸缩小的比例（如0.3，有ratio的时候可不填图片比例）,
                      save_q:保存的图片质量}
        :return: dst_img
        """
        args_key = {'ori_img': '', 'dst_img': '', 'dst_w': '', 'dst_h': '', 'ratio': '', 'save_q': 75}
        arg = {}
        for key in args_key:
            if key in args:
                arg[key] = args[key]

        ori_img = arg['ori_img']
        im = image.open(ori_img)
        ori_w, ori_h = im.size
        width_ratio = height_ratio = None
        save_q = arg['save_q']
        ratio = args.get('ratio')
        shuffix = ori_img.split('.')[-1]
        if ratio:
            if max(ori_w, ori_h) < 1000:
                new_width = ori_w
                new_height = ori_h
                save_q = 100
            else:
                new_width = int(ori_w * ratio)
                new_height = int(ori_h * ratio)
        else:
            ratio = 1
            if (ori_w and ori_w > arg['dst_w']) or (ori_h and ori_h > arg['dst_h']):
                if arg['dst_w'] and ori_w > arg['dst_w']:
                    width_ratio = float(arg['dst_w']) / ori_w  # 正确获取小数的方式
                if arg['dst_h'] and ori_h > arg['dst_h']:
                    height_ratio = float(arg['dst_h']) / ori_h

                if width_ratio and height_ratio:
                    if width_ratio < height_ratio:
                        ratio = width_ratio
                    else:
                        ratio = height_ratio

                if width_ratio and not height_ratio:
                    ratio = width_ratio
                if height_ratio and not width_ratio:
                    ratio = height_ratio

                new_width = int(ori_w * ratio)
                new_height = int(ori_h * ratio)
            else:
                new_width = ori_w
                new_height = ori_h

        dst_img = ori_img + '_' + str(new_width) + 'x' + str(new_height) + '.' + shuffix  # 拼接图片尺寸在最后
        im.resize((new_width, new_height), image.ANTIALIAS).save(dst_img, quality=save_q)

        # 根据EXIF旋转压缩后的图片为正确可读方向
        old_img = image.open(dst_img)
        if hasattr(im, '_getexif'):
            # 获取exif信息
            dict_exif = im._getexif()
            # print(dict_exif)
            if dict_exif:
                rotate_status = dict_exif.get(274)
                if rotate_status == 6:  # 竖直屏幕拍摄的情况
                    rotated = old_img.rotate(-90, expand=True)
                elif rotate_status == 8:  # 倒置手机拍摄
                    rotated = old_img.rotate(90, expand=True)
                elif rotate_status == 3:  # 右侧水平拍摄
                    rotated = old_img.rotate(180, expand=True)
                else:
                    rotated = old_img
                rotated.save(dst_img)

        '''
        image.ANTIALIAS还有如下值：
        NEAREST: use nearest neighbour
        BILINEAR: linear interpolation in a 2x2 environment
        BICUBIC:cubic spline interpolation in a 4x4 environment
        ANTIALIAS:best down-sizing filter
        '''
        return dst_img

    # 裁剪压缩图片
    @staticmethod
    def clip_resize_img(**args):
        args_key = {'ori_img': '', 'dst_img': '', 'dst_w': '', 'dst_h': '', 'save_q': 75}
        arg = {}
        for key in args_key:
            if key in args:
                arg[key] = args[key]

        im = image.open(arg['ori_img'])
        ori_w, ori_h = im.size

        dst_scale = float(arg['dst_h']) / arg['dst_w']  # 目标高宽比
        ori_scale = float(ori_h) / ori_w  # 原高宽比

        if ori_scale >= dst_scale:
            # 过高
            width = ori_w
            height = int(width * dst_scale)

            x = 0
            y = (ori_h - height) / 3

        else:
            # 过宽
            height = ori_h
            width = int(height * dst_scale)

            x = (ori_w - width) / 2
            y = 0

        # 裁剪
        box = (x, y, width + x, height + y)
        # 这里的参数可以这么认为：从某图的(x,y)坐标开始截，截到(width+x,height+y)坐标
        # 所包围的图像，crop方法与php中的imagecopy方法大为不一样
        new_img = im.crop(box)
        im = None

        # 压缩
        ratio = float(arg['dst_w']) / width
        new_width = int(width * ratio)
        new_height = int(height * ratio)
        new_img.resize((new_width, new_height), image.ANTIALIAS).save(arg['dst_img'], quality=arg['save_q'])

    # 水印(这里仅为图片水印)
    @staticmethod
    def water_mark(**args):
        args_key = {'ori_img': '', 'dst_img': '', 'mark_img': '', 'water_opt': ''}
        arg = {}
        for key in args_key:
            if key in args:
                arg[key] = args[key]

        im = image.open(arg['ori_img'])
        ori_w, ori_h = im.size

        mark_im = image.open(arg['mark_img'])
        mark_w, mark_h = mark_im.size
        option = {'leftup': (0, 0), 'rightup': (ori_w - mark_w, 0), 'leftlow': (0, ori_h - mark_h),
                  'rightlow': (ori_w - mark_w, ori_h - mark_h)
                  }

        im.paste(mark_im, option[arg['water_opt']], mark_im.convert('RGBA'))
        im.save(arg['dst_img'])


"""
if __name__ == '__main__':
    test = CompressPicture()
    # Demon
    # 源图片
    ori_img = '/home/wiilz/Downloads/aziz-acharki-1203210-unsplash.jpg'
    # 水印标
    mark_img = 'D:/mark.png'
    # 水印位置(右下)
    water_opt = 'rightlow'
    # 目标图片
    dst_img = '/home/wiilz/Downloads/ccc.jpg'
    # 目标图片大小
    dst_w = 94
    dst_h = 94
    # 保存的图片质量
    save_q = 35
    # 裁剪压缩
    # clipResizeImg(ori_img=ori_img, dst_img=dst_img, dst_w=dst_w, dst_h=dst_h, save_q=save_q)
    # 等比例压缩
    test.resize_img(ori_img=ori_img, dst_img=dst_img, ratio=0.5, save_q=20)
    # 水印
    # waterMark(ori_img=ori_img,dst_img=dst_img,mark_img=mark_img,water_opt=water_opt)
"""