import json
import os
# import threading
import uuid
from datetime import datetime
from decimal import Decimal

import requests
import xlrd

from flask import request, current_app, send_from_directory
# from gevent import thread


from planet.common.error_response import ParamsError, AuthorityError
from planet.common.params_validates import parameter_required
from planet.common.success_response import Success
from planet.common.token_handler import is_admin, is_supplizer, token_required
from planet.config.enums import ProductFrom
from planet.control.BaseControl import BASEAPPROVAL
from planet.extensions.tasks import get_url_local, auto_agree_task
from planet.extensions.register_ext import db

from planet.models import ProductBrand, ProductCategory, Products, ProductImage, ProductSku, Items, \
    ProductItems


class CExcel():
    # 头部参数配置文件
    heads_config = ('商品编码', '货号', '三级类目', '品牌', '场景标签', '商品名称', '商品描述', '划线价格', '商品运费', '商品主图',
                    '顶部轮播图1', '顶部轮播图2', '顶部轮播图3', '顶部轮播图4', '顶部轮播图5', '顶部轮播图6', '顶部轮播图7',
                    '顶部轮播图8', '顶部轮播图9', '底部长图1', '底部长图2', '底部长图3', '底部长图4', '底部长图5', '底部长图6',
                    '底部长图7', '底部长图8', '底部长图9', '底部长图10', '底部长图11', '底部长图12', '底部长图13', '底部长图14',
                    '底部长图15', '底部长图16', '底部长图17', '底部长图18', '底部长图19', '底部长图20', '底部长图21',
                    '底部长图22', '底部长图23', '底部长图24', '底部长图25', '底部长图26', '底部长图27', '底部长图28',
                    '底部长图29', '底部长图30', 'SKU属性名', 'SKU属性值', 'SKU图', 'SKU库存', '让利比', 'SKU价格')

    def __init__(self):
        self._url_list = list()

    @token_required
    def upload_products_file(self):
        """
        文件上传入口
        :return:
        """
        file = request.files.get('file')
        data = parameter_required()
        current_app.logger.info('start add template {}'.format(datetime.now()))
        folder = 'xls'
        # 接收数据保存到服务器
        file_path = self._save_excel(file, folder)
        self._insertproduct(file_path)
        if self._url_list:
            get_url_local.apply_async(args=[self._url_list], countdown=1, expires=1 * 60, )
            self._url_list = list()
        current_app.logger.info('end add template {}'.format(datetime.now()))
        return Success('上传成功')

    def _save_excel(self, file, folder):
        """
        保存文件到本地，方便后续读取数据
        :param file:
        :param folder:
        :return:
        """
        filename = file.filename
        shuffix = os.path.splitext(filename)[-1]
        current_app.logger.info(">>>  Upload File Shuffix is {0}  <<<".format(shuffix))
        shuffix = shuffix.lower()
        if self._allowed_file(shuffix):
            img_name = self._new_name(shuffix)
            time_now = datetime.now()
            year = str(time_now.year)
            month = str(time_now.month)
            day = str(time_now.day)
            newPath = os.path.join(current_app.config['BASEDIR'], 'img', folder, year, month, day)
            if not os.path.isdir(newPath):
                os.makedirs(newPath)
            newFile = os.path.join(newPath, img_name)
            file.save(newFile)  # 保存文件
            # data = '/img/{folder}/{year}/{month}/{day}/{img_name}'.format(folder=folder, year=year,
            #                                                               month=month, day=day,
            #                                                               img_name=img_name)
            current_app.logger.info(">>>  Upload File Path is  {}  <<<".format(newFile))
            return newFile
        else:
            raise SystemError(u'上传有误, 不支持的文件类型 {}'.format(shuffix))

    def _allowed_file(self, shuffix):
        """
        文件格式校验
        :param shuffix:
        :return:
        """
        return shuffix in ['.xls', '.xlsm', '.xlsx']

    def _new_name(self, shuffix):
        """
        重命名接收文件。防止有异常字符干扰服务器正常运行
        :param shuffix:
        :return:
        """
        import string, random
        myStr = string.ascii_letters + '12345678'
        try:
            usid = request.user.id
        except AttributeError as e:
            usid = 'anonymous'
        res = datetime.now().strftime('%Y-%m-%d_%H:%M:%S.%f') + random.choice(myStr) + usid + shuffix
        return res

    def _insertproduct(self, filepath):
        """
        读取Excel 并将数据存入数据库
        :param filepath:
        :return:
        """
        excel_file = xlrd.open_workbook(filepath)
        # 读取Excel数据
        content_sheet = excel_file.sheet_by_name('product')
        heads = dict()
        # 读取文件首行表头配置 防止行位置变更
        heads_content = content_sheet.row(0)
        for index, title in enumerate(heads_content):
            if title.value in self.heads_config:
                heads.setdefault(title.value, index)

        # print(heads)
        prcode_dict = {}
        # 记录商品编号，重复编号不予操作
        with db.auto_commit():

            # all_instance_list = []
            # 开始按行读取文件信息
            for row_num in range(1, content_sheet.nrows):
                row_content = content_sheet.row(row_num)
                prcode = row_content[heads.get('商品编码')].value
                if not prcode:
                    continue
                if prcode not in prcode_dict:
                    # 商品首次读取，进行插入或更新操作。
                    instance_list = self._update_product(heads, row_content, row_num, prcode_dict)
                    # all_instance_list.extend(instance_list)

                    db.session.add_all(instance_list)
                else:
                    # 非首次商品读取，商品只累加库存。sku进行插入或更新
                    sku_instance, skuid = self._update_productsku(heads, row_content, row_num, prcode_dict)
                    db.session.add(sku_instance)
                    prcode_dict.get(prcode).get('skuid').append(skuid)

                db.session.flush()

            for prcode in prcode_dict:
                # product = Products.query.filter(Products.PRcode == prcode, Products.isdelete == False).first()
                product = prcode_dict.get(prcode).get('product')

                ProductSku.query.filter(
                    ProductSku.isdelete == False,
                    ProductSku.PRid == product.PRid,
                    ProductSku.SKUid.notin_(prcode_dict.get(prcode).get('skuid'))).delete_(synchronize_session=False)
                db.session.add(product)

        for prcode in prcode_dict:
            product = prcode_dict.get(prcode).get('product')

            if product.PRstocks != 0:
                # todo 审核中的编辑会 重复添加审批
                avid = BASEAPPROVAL().create_approval('toshelves', request.user.id, product.PRid, product.PRfrom)
                # 5 分钟后自动通过
                auto_agree_task.apply_async(args=[avid], countdown=5 * 60, expires=10 * 60, )

    def _update_product(self, heads, row, row_num, prcode_dict):
        """
        首行商品数据 统一更新或添加
        :param heads:
        :param row:
        :param row_num:
        :return:
        """
        prid = str(uuid.uuid1())
        instance_list = []
        if is_admin():
            product_from = ProductFrom.platform.value

        elif is_supplizer():
            product_from = ProductFrom.supplizer.value
        else:
            raise AuthorityError()

        prcode = str(row[heads.get('商品编码')].value)
        pbname = str(row[heads.get('品牌')].value)
        pcname = str(row[heads.get('三级类目')].value)
        # 类目和品牌获取
        try:
            pbid = self._get_pbid(pbname)
        except:
            current_app.logger.info('row = {} 品牌 {} 找不到 '.format(row_num, pbname))
            raise ParamsError('{}行 品牌 {} 有误 '.format(row_num, pbname))

        try:
            pcid = self._get_pcid(pcname)
        except:
            current_app.logger.info('row = {} 三级类目 {} 找不到 '.format(row_num, pcname))
            raise ParamsError('{}行 三级类目 {} 有误 '.format(row_num, pcname))

        prdesc = []
        # 商品底部长图拼接并保存
        for i in range(1, 31):
            tmptitle = '底部长图{}'.format(i)
            if not heads.get(tmptitle) or not row[heads.get(tmptitle)].value:
                continue
            product_url = row[heads.get(tmptitle)].value
            self.save_url(product_url)
            prdesc.append(product_url)

        product_instance = Products.query.filter(Products.PRcode == str(row[heads.get('商品编码')].value)).first()
        productmain = row[heads.get('商品主图')].value
        if not productmain:
            raise ParamsError('{} 行 商品主图丢失'.format(row_num))
        self.save_url(productmain)
        prattribute = json.dumps(str(row[heads.get('SKU属性名')].value).split('|'))
        # 商品保存或更新
        product_dict = {
                'PRtitle': row[heads.get('商品名称')].value,
                # 'PRprice': row[heads.get('商品名称')].value,
                'PRlinePrice': float('%.2f' % float(str(row[heads.get('划线价格')].value))),
                'PRfreight': float('%.2f' % float(str(row[heads.get('商品运费')].value))),
                'PRmainpic': productmain,
                'PCid': pcid,
                'PBid': pbid,
                'PRdesc': json.dumps(prdesc),
                'PRattribute': prattribute,
                'PRremarks': "{}",
                'PRfrom': product_from,
                'PRdescription': row[heads.get('商品描述')].value,  # 描述
                'PRcode': prcode,
                'PRstocks': int(row[heads.get('SKU库存')].value),
                # 'PRfeatured': row[heads.get('商品名称')].value,  # 是否为精选
            }

        if not product_instance:
            product_dict.setdefault('PRid', prid)
            product_dict.setdefault('CreaterId', request.user.id,)
            # product_dict.setdefault('CreaterId', 'id')
            product_dict.setdefault('PRprice', row[heads.get('SKU价格')].value)
            # product_dict.setdefault('PRstocks', int(row[heads.get('SKU库存')].value))
            product_instance = Products.create(product_dict)
        else:
            prid = product_instance.PRid
            product_instance.update(product_dict)

        # instance_list.append(product_instance)
        # prcode_dict.get(prcode).setdefault('product', product_instance)
        # prcode_dict.get(prcode).setdefault('skuid', [])

        product_img_list = []
        # 商品轮播图
        for i in range(1, 10):
            tmptitle = '顶部轮播图{}'.format(i)
            if not heads.get(tmptitle) or not row[heads.get(tmptitle)].value:
                continue
            product_img_url = row[heads.get(tmptitle)].value
            self.save_url(product_img_url)
            pi_instance = ProductImage.query.filter(
                ProductImage.PRid == prid,
                ProductImage.isdelete == False,
                ProductImage.PIpic == product_img_url
            ).first()
            if pi_instance:
                pi_instance.PIsort = i
            else:
                pi_instance = ProductImage.create({
                    'PIid': str(uuid.uuid1()),
                    'PRid': prid,
                    'PIpic': product_img_url,
                    'PIsort': i
                })
            product_img_list.append(pi_instance.PIid)
            instance_list.append(pi_instance)

        ProductImage.query.filter(
            ProductImage.PIid.notin_(product_img_list),
            ProductImage.isdelete == False,
            ProductImage.PRid == prid).delete_(synchronize_session=False)

        sku_instance, skuid = self._deal_sku(prid, row, heads, row_num)

        instance_list.append(sku_instance)

        # 标签
        items = str(row[heads.get('场景标签')].value).split('|')
        piid_list = []
        if items:
            if product_from == ProductFrom.supplizer.value and len(items) > 3:
                raise ParamsError('最多只能关联3个标签')
            for item in items:

                item_instance = Items.query.filter(Items.ITname == item, Items.isdelete == False).first()
                if not item_instance or item_instance.ITid == 'planet_featured':
                    continue
                item_product = ProductItems.query.filter(
                    ProductItems.isdelete == False,
                    ProductItems.ITid == item_instance.ITid,
                    ProductItems.PRid == prid).first()
                if not item_product:
                    item_product = ProductItems.create({
                        'PIid': str(uuid.uuid1()),
                        'PRid': prid,
                        'ITid': item_instance.ITid
                    })
                    instance_list.append(item_product)
                piid_list.append(item_product.PIid)
        # 同一商品无效标签删除
        ProductItems.query.filter(
            ProductItems.PRid == prid,
            ProductItems.isdelete == False,
            ProductItems.PIid.notin_(piid_list)).delete_(synchronize_session=False)

        prcode_dict.setdefault(prcode, {'product': product_instance, 'skuid': [skuid, ]})
        return instance_list

    def _update_productsku(self, heads, row, row_num, prcode_dict):
        """
        非首行商品数据，进行sku数据更新或添加。并更新商品库存数据
        :param heads:
        :param row:
        :param row_num:
        :return:
        """
        # product_instance = Products.query.filter(
        #     Products.PRcode == str(row[heads.get('商品编码')].value), Products.isdelete == False).first()
        product_instance = prcode_dict.get(str(row[heads.get('商品编码')].value)).get('product')
        product_instance.PRstocks += int(row[heads.get('SKU库存')].value)
        return self._deal_sku(product_instance.PRid, row, heads, row_num)

    def save_url(self, product_url):
        """异步获取url对应资源并保存到当前服务器backup文件夹"""
        if not product_url:
            return
        # lock = threading.Lock()
        self._url_list.append(product_url)
        # current_app.logger.info('start new thread to save {}'.format(product_url))


        # current_app.logger.info('end save {}'.format(product_url))

    def _get_pbid(self, pbname):
        pb = ProductBrand.query.filter(
            ProductBrand.isdelete == False,
            ProductBrand.PBname == pbname).order_by(
            ProductBrand.createtime.desc()).first()
        if not pb:
            raise ParamsError('品牌名称有误')
        return pb.PBid

    def _get_pcid(self, pcname):
        pc = ProductCategory.query.filter(
            ProductCategory.isdelete == False,
            ProductCategory.PCtype == 3,
            ProductCategory.PCname == pcname).order_by(ProductCategory.createtime.desc()).first()
        if not pc:
            raise ParamsError('分类名称有误')
        return pc.PCid

    def _deal_sku(self, prid, row, heads, row_num):
        """
        新增或更新sku
        :param prid:
        :param row:
        :param heads:
        :param row_num:
        :return:
        """
        skuid = str(uuid.uuid1())
        # 当前行的商品sku
        skupic = str(row[heads.get('SKU图')].value)
        if not skupic:
            raise ParamsError('{} 行 sku 图片数据异常'.format(row_num))
        self.save_url(skupic)

        skuattritedetail = json.dumps(str(row[heads.get('SKU属性值')].value))
        sku_dict = {
            'PRid': prid,
            'SKUpic': skupic,
            'SKUprice': Decimal(str(row[heads.get('SKU价格')].value)),
            'SKUstock': int(row[heads.get('SKU库存')].value),
            'SKUattriteDetail': skuattritedetail,
            'SKUsn': str(row[heads.get('货号')].value),
            'SkudevideRate': Decimal(str(row[heads.get('让利比')].value))
        }
        sku_instance = ProductSku.query.filter(
            ProductSku.isdelete == False, ProductSku.SKUattriteDetail == skuattritedetail, ProductSku.PRid == prid
        ).first()
        if sku_instance:
            skuid = sku_instance.SKUid
            sku_instance.update(sku_dict)
        else:
            sku_dict.setdefault('SKUid', skuid)
            sku_instance = ProductSku.create(sku_dict)
        return sku_instance, skuid

    @token_required
    def download(self):
        if not is_supplizer() and not is_admin():
            raise AuthorityError()
        current_app.logger.info('start download template')

        template_path = os.path.join(current_app.config['BASEDIR'], 'img', 'xls')
        current_app.logger.info('template path {}'.format(template_path))
        current_app.logger.info('is file {}'.format(os.path.isfile(os.path.join(template_path, 'template.xlsx'))))
        return send_from_directory(template_path, 'template.xlsx', as_attachment=True)


if __name__ == '__main__':
    # app = create_app()
    # with app.app_context():
    #     cexcel = CExcel()
    #     filepath = r'D:\QQ\微信\file\WeChat Files\wxid_wnsa7sn01tu922\FileStorage\File\2019-03\product_insert.xlsx'
    #     # filepath = 'C:\Users\刘帅斌\Desktop\product_insert.xlsx'
    #     # cexcel.insertproduct(filepath)  urllib.request.urlretrieve
    #     cexcel._insertproduct(filepath)
    #     pass
    pass
