import os
import uuid
from datetime import datetime

import xlrd
from six.moves import urllib
# from flask import request, current_app
#
# from planet.common.params_validates import parameter_required
# from planet.common.success_response import Success


class CExcel():
    heads_config = ('商品编码', '货号', '三级类目', '品牌', '场景标签', '商品名称', '商品描述', '划线价格', '商品运费', '商品主图',
                    '顶部轮播图1', '顶部轮播图2', '顶部轮播图3', '顶部轮播图4', '顶部轮播图5', '顶部轮播图6', '顶部轮播图7',
                    '顶部轮播图8', '顶部轮播图9', '底部长图1', '底部长图2', '底部长图3', '底部长图4', '底部长图5', '底部长图6',
                    '底部长图7', '底部长图8', '底部长图9', '底部长图10', '底部长图11', '底部长图12', '底部长图13', '底部长图14',
                    '底部长图15', '底部长图16', '底部长图17', '底部长图18', '底部长图19', '底部长图20', '底部长图21',
                    '底部长图22', '底部长图23', '底部长图24', '底部长图25', '底部长图26', '底部长图27', '底部长图28',
                    '底部长图29', '底部长图30', 'SKU属性名', 'SKU属性值', 'SKU图', 'SKU库存', '让利比', 'SKU价格')

    # def upload_products_file(self):
    #     file = request.files.get('file')
    #     data = parameter_required()
    #     folder = 'xls'
    #     file_path = self._save_excel(file, folder)
    #     return Success('上传成功')
    #
    #
    # def _save_excel(self, file, folder):
    #     filename = file.filename
    #     shuffix = os.path.splitext(filename)[-1]
    #     current_app.logger.info(">>>  Upload File Shuffix is {0}  <<<".format(shuffix))
    #     shuffix = shuffix.lower()
    #     if self.allowed_file(shuffix):
    #         img_name = self.new_name(shuffix)
    #         time_now = datetime.now()
    #         year = str(time_now.year)
    #         month = str(time_now.month)
    #         day = str(time_now.day)
    #         newPath = os.path.join(current_app.config['BASEDIR'], 'img', folder, year, month, day)
    #         if not os.path.isdir(newPath):
    #             os.makedirs(newPath)
    #         newFile = os.path.join(newPath, img_name)
    #         file.save(newFile)  # 保存文件
    #         data = '/img/{folder}/{year}/{month}/{day}/{img_name}'.format(folder=folder, year=year,
    #                                                                       month=month, day=day,
    #                                                                       img_name=img_name)
    #         current_app.logger.info(">>>  Upload File Path is  {}  <<<".format(data))
    #         return data
    #     else:
    #         raise SystemError(u'上传有误, 不支持的文件类型 {}'.format(shuffix))
    #
    # def allowed_file(self, shuffix):
    #     return shuffix in ['xls', 'xlsm', 'xlsx']
    #
    # def new_name(self, shuffix):
    #     import string, random
    #     myStr = string.ascii_letters + '12345678'
    #     try:
    #         usid = request.user.id
    #     except AttributeError as e:
    #         usid = 'anonymous'
    #     res = datetime.now().strftime('%Y-%m-%d_%H:%M:%S.%f') + random.choice(myStr) + usid + shuffix
    #     return res

    def insertproduct(self, filepath):
        excel_file = xlrd.open_workbook(filepath)
        content_sheet = excel_file.sheet_by_name('product')


        heads = dict()

        heads_content = content_sheet.row(0)
        for index, title in enumerate(heads_content):
            if title.value in self.heads_config:
                heads.setdefault(title.value, index)

        print(heads)
        prcode_list = []
        for row_num in range(1, content_sheet.nrows):
            row_content = content_sheet.row(row_num)
            prcode = row_content[heads.get('商品编码')].value
            if prcode not in prcode_list:
                prcode_list.append(prcode)
                prid = str(uuid.uuid1())
                # 商品
                self._get_product_dict(heads, row_content, prid)

    def _get_product_dict(self, heads, row, prid):
        # todo 身份不同，from 不同，createid 不同
        product_from = 10
        product_dict = {
            'PRid': prid,
            'PRtitle': row[heads.get('商品名称')].value,
            # 'PRprice': row[heads.get('商品名称')].value,
            'PRlinePrice': float('%.2f' % str(row[heads.get('划线价格')].value)),
            'PRfreight': float('%.2f' % str(row[heads.get('商品运费')].value)),
            'PRstocks': int(row[heads.get('SKU库存')].value),
            'PRmainpic': row[heads.get('商品主图')].value,
            'PCid': row[heads.get('商品名称')].value,
            'PBid': row[heads.get('商品名称')].value,
            'PRdesc': row[heads.get('商品名称')].value,
            'PRattribute': row[heads.get('商品名称')].value,
            'PRremarks': row[heads.get('商品名称')].value,
            'PRfrom': product_from,
            'CreaterId': 'id',
            'PRdescription': row[heads.get('商品名称')].value,  # 描述
            # 'PRfeatured': row[heads.get('商品名称')].value,  # 是否为精选
        }

    def _get_url_local(self, url):
        # local_url =
        pass

if __name__ == '__main__':
    # cexcel = CExcel()
    # filepath = r'D:\QQ\微信\file\WeChat Files\wxid_wnsa7sn01tu922\FileStorage\File\2019-03\product_insert.xlsx'
    # cexcel.insertproduct(filepath)  urllib.request.urlretrieve
    pass
