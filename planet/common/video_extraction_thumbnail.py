# -*- coding: utf-8 -*-
import os
import cv2

from planet.common.error_response import ParamsError

""" 视频截取缩略图 """


def video2frames(pathin,  # 视频的路径
                 pathout,  # 设定提取的图片保存在哪个文件夹下
                 only_output_video_info=False,  # 如果为True，只输出视频信息（长度、帧数和帧率），不提取图片
                 extract_time_points=None,  # 提取的时间点，单位为秒，为元组数据，如(2, 3, 5)
                 initial_extract_time=0,  # 提取的起始时刻，单位为秒，默认为0（即从视频最开始提取）
                 end_extract_time=None,  # 提取的终止时刻，单位为秒，默认为None（即视频终点）
                 extract_time_interval=-1,  # 提取的时间间隔，单位为秒，默认为-1（即输出时间范围内的所有帧）
                 output_prefix='frame',  # 图片的前缀名，默认为frame，图片的名称将为frame_000001.jpg
                 jpg_quality=100,  # 设置图片质量，范围为0到100，默认为100（质量最佳）
                 iscolor=True):  # 如果为False，输出的将是黑白图片
    """
    pathin：视频的路径，比如：F:\python_tutorials\test.mp4
    pathout：设定提取的图片保存在哪个文件夹下，比如：F:\python_tutorials\frames1\。如果该文件夹不存在，函数将自动创建它
    only_output_video_info：如果为True，只输出视频信息（长度、帧数和帧率），不提取图片
    extract_time_points：提取的时间点，单位为秒，为元组数据，比如，(2, 3, 5)表示只提取视频第2秒， 第3秒，第5秒图片
    initial_extract_time：提取的起始时刻，单位为秒，默认为0（即从视频最开始提取）
    end_extract_time：提取的终止时刻，单位为秒，默认为None（即视频终点）
    extract_time_interval：提取的时间间隔，单位为秒，默认为-1（即输出时间范围内的所有帧）
    output_prefix：图片的前缀名，默认为frame，图片的名称将为frame_000001.jpg、frame_000002.jpg、frame_000003.jpg......
    jpg_quality：设置图片质量，范围为0到100，默认为100（质量最佳）
    iscolor：如果为False，输出的将是黑白图片
    """

    cap = cv2.VideoCapture(pathin)  # 打开视频文件
    n_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))  # 视频的帧数
    fps = cap.get(cv2.CAP_PROP_FPS)  # 视频的帧率
    dur = n_frames / fps  # 视频的时间
    thumbnail_name_list = []
    if int(dur) > 60:
        os.remove(pathin)
        raise ParamsError('视频时长不能超过60秒')
    if int(dur) < 3:
        os.remove(pathin)
        raise ParamsError('视频时长不能少于3秒')
    # 如果only_output_video_info=True, 只输出视频信息，不提取图片
    if only_output_video_info:
        print('only output the video information (without extract frames)::::::')
        print("Duration of the video: {} seconds".format(dur))
        print("Number of frames: {}".format(n_frames))
        print("Frames per second (FPS): {}".format(fps))

    # 提取特定时间点图片
    elif extract_time_points is not None:
        if max(extract_time_points) > dur:  # 判断时间点是否符合要求
            # raise NameError('the max time point is larger than the video duration....')
            print('the max time point is larger than the video duration....')
            extract_time_points = (0.1,)
        try:
            os.mkdir(pathout)
        except OSError:
            pass
        success = True
        count = 0
        while success and count < len(extract_time_points):
            cap.set(cv2.CAP_PROP_POS_MSEC, (1000 * extract_time_points[count]))
            success, image = cap.read()
            if success:
                if not iscolor:
                    image = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)  # 转化为黑白图片
                print('Write a new frame: {}, {}th'.format(success, count + 1))
                # cv2.imwrite(os.path.join(pathout, "{}{}_{:06d}.jpg".format(str(dur)[:6], output_prefix, count + 1)), image,
                #             [int(cv2.IMWRITE_JPEG_QUALITY), jpg_quality])  # save frame as JPEG file
                thumbnail_name = "{}_{:06d}.jpg".format( output_prefix, count + 1)
                cv2.imwrite(os.path.join(pathout, thumbnail_name), image, [int(cv2.IMWRITE_JPEG_QUALITY), jpg_quality]) # save frame as JPEG file
                count = count + 1
                thumbnail_name_list.append(thumbnail_name)

    else:
        # 判断起始时间、终止时间参数是否符合要求
        if initial_extract_time > dur:
            raise NameError('initial extract time is larger than the video duration....')
        if end_extract_time is not None:
            if end_extract_time > dur:
                raise NameError('end extract time is larger than the video duration....')
            if initial_extract_time > end_extract_time:
                raise NameError('end extract time is less than the initial extract time....')

        # 时间范围内的每帧图片都输出
        if extract_time_interval == -1:
            if initial_extract_time > 0:
                cap.set(cv2.CAP_PROP_POS_MSEC, (1000 * initial_extract_time))
            try:
                os.mkdir(pathout)
            except OSError:
                pass
            print('Converting a video into frames......')
            if end_extract_time is not None:
                N = (end_extract_time - initial_extract_time) * fps + 1
                success = True
                count = 0
                while success and count < N:
                    success, image = cap.read()
                    if success:
                        if not iscolor:
                            image = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
                        print('Write a new frame: {}, {}/{}'.format(success, count + 1, n_frames))
                        # cv2.imwrite(os.path.join(pathout, "{}_{:06d}.jpg".format(output_prefix, count + 1)), image,
                        #             [int(cv2.IMWRITE_JPEG_QUALITY), jpg_quality])  # save frame as JPEG file
                        thumbnail_name = "{}_{:06d}.jpg".format(output_prefix, count + 1)
                        cv2.imwrite(os.path.join(pathout, thumbnail_name), image,
                                    [int(cv2.IMWRITE_JPEG_QUALITY), jpg_quality])  # save frame as JPEG file
                        count = count + 1
                        thumbnail_name_list.append(thumbnail_name)
            else:
                success = True
                count = 0
                while success:
                    success, image = cap.read()
                    if success:
                        if not iscolor:
                            image = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
                        print('Write a new frame: {}, {}/{}'.format(success, count + 1, n_frames))
                        # cv2.imwrite(os.path.join(pathout, "{}_{:06d}.jpg".format(output_prefix, count + 1)), image,
                        #             [int(cv2.IMWRITE_JPEG_QUALITY), jpg_quality])  # save frame as JPEG file
                        thumbnail_name = "{}_{:06d}.jpg".format(output_prefix, count + 1)
                        cv2.imwrite(os.path.join(pathout, thumbnail_name), image,
                                    [int(cv2.IMWRITE_JPEG_QUALITY), jpg_quality])  # save frame as JPEG file
                        count = count + 1
                        thumbnail_name_list.append(thumbnail_name)

        # 判断提取时间间隔设置是否符合要求
        elif extract_time_interval > 0 and extract_time_interval < 1 / fps:
            raise NameError('extract_time_interval is less than the frame time interval....')
        elif extract_time_interval > (n_frames / fps):
            raise NameError('extract_time_interval is larger than the duration of the video....')

        # 时间范围内每隔一段时间输出一张图片
        else:
            try:
                os.mkdir(pathout)
            except OSError:
                pass
            print('Converting a video into frames......')
            if end_extract_time is not None:
                N = (end_extract_time - initial_extract_time) / extract_time_interval + 1
                success = True
                count = 0
                while success and count < N:
                    cap.set(cv2.CAP_PROP_POS_MSEC, (1000 * initial_extract_time + count * 1000 * extract_time_interval))
                    success, image = cap.read()
                    if success:
                        if not iscolor:
                            image = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
                        print('Write a new frame: {}, {}th'.format(success, count + 1))
                        # cv2.imwrite(os.path.join(pathout, "{}_{:06d}.jpg".format(output_prefix, count + 1)), image,
                        #             [int(cv2.IMWRITE_JPEG_QUALITY), jpg_quality])  # save frame as JPEG file
                        thumbnail_name = "{}_{:06d}.jpg".format(output_prefix, count + 1)
                        cv2.imwrite(os.path.join(pathout, thumbnail_name), image,
                                    [int(cv2.IMWRITE_JPEG_QUALITY), jpg_quality])  # save frame as JPEG file
                        count = count + 1
                        thumbnail_name_list.append(thumbnail_name)
            else:
                success = True
                count = 0
                while success:
                    cap.set(cv2.CAP_PROP_POS_MSEC, (1000 * initial_extract_time + count * 1000 * extract_time_interval))
                    success, image = cap.read()
                    if success:
                        if not iscolor:
                            image = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
                        print('Write a new frame: {}, {}th'.format(success, count + 1))
                        # cv2.imwrite(os.path.join(pathout, "{}_{:06d}.jpg".format(output_prefix, count + 1)), image,
                        #             [int(cv2.IMWRITE_JPEG_QUALITY), jpg_quality])  # save frame as JPEG file
                        thumbnail_name = "{}_{:06d}.jpg".format(output_prefix, count + 1)
                        cv2.imwrite(os.path.join(pathout, thumbnail_name), image,
                                    [int(cv2.IMWRITE_JPEG_QUALITY), jpg_quality])  # save frame as JPEG file
                        count = count + 1
                        thumbnail_name_list.append(thumbnail_name)

    re_data = {"thumbnail_name_list": thumbnail_name_list,
               "video_duration": dur}
    return re_data

# """测试"""
# pathin = 'D:\qrcode\ceui.mp4'
# # # video2frames(pathin, only_output_video_info=True)
# #
# pathout = 'D:\qrcode'
# video2frames(pathin, pathout, extract_time_points=(2,), jpg_quality=50)
#
# pathout = './frames2'
# video2frames(pathin, pathout, extract_time_points=(1, 2, 5))
#
# pathout = './frames3'
# video2frames(pathin, pathout,
#              initial_extract_time=1,
#              end_extract_time=3,
#              extract_time_interval=0.5)
#
# pathout = './frames4/'
# video2frames(pathin, pathout, extract_time_points=(0.3, 2), iscolor=False)
#
# pathout = './frames5/'
# video2frames(pathin, pathout, extract_time_points=(0.3, 2), jpg_quality=50)
