import uuid
from datetime import datetime, date
from decimal import Decimal

import json

from flask import current_app

from planet.config.enums import ApprovalType, ApplyStatus, ApprovalAction, ApplyFrom, UserMediaType, \
    TrialCommodityStatus
from planet.common.error_response import SystemError, ParamsError
from planet.common.request_handler import gennerc_log
from planet.extensions.register_ext import db
from planet.models import User, Supplizer, Admin, PermissionType, News, Approval, ApprovalNotes, Permission, CashNotes, \
    UserWallet, UserMedia, Products, ActivationCodeApply, TrialCommoditySkuValue, TrialCommodityImage, \
    TrialCommoditySku, ProductBrand, TrialCommodity, FreshManFirstProduct, ProductSku, FreshManFirstSku, \
    FreshManFirstApply, MagicBoxApply, GuessNumAwardApply, ProductCategory, ProductSkuValue, Base, SettlenmentApply, \
    SupplizerSettlement, ProductImage
from planet.service.SApproval import SApproval
from json import JSONEncoder as _JSONEncoder


class JSONEncoder(_JSONEncoder):
    """重写对象序列化, 当默认jsonify无法序列化对象的时候将调用这里的default"""

    def default(self, o):

        if hasattr(o, 'keys') and hasattr(o, '__getitem__'):
            res = dict(o)
            new_res = {k.lower(): v for k, v in res.items()}
            return new_res
        if isinstance(o, datetime):
            # 也可以序列化时间类型的对象
            return o.strftime('%Y-%m-%d %H:%M:%S')
        if isinstance(o, date):
            return o.strftime('%Y-%m-%d')
        if isinstance(o, type):
            raise o()
        if isinstance(o, Decimal):
            return round(float(o), 2)

        raise TypeError(repr(o) + " is not JSON serializable")


class BASEAPPROVAL():
    sapproval = SApproval()

    def create_approval(self, avtype, startid, avcontentid, applyfrom=None, **kwargs):

        gennerc_log('start create approval ptid = {0}'.format(avtype))
        pt = PermissionType.query.filter_by_(PTid=avtype).first_('参数异常')

        start, content = self.__get_approvalcontent(pt, startid, avcontentid, applyfrom=applyfrom, **kwargs)
        db.session.expunge_all()
        av = Approval.create({
            "AVid": str(uuid.uuid1()),
            "AVname": avtype + datetime.now().strftime('%Y%m%d%H%M%S'),
            "PTid": avtype,
            "AVstartid": startid,
            "AVlevel": 1,
            "AVstatus": ApplyStatus.wait_check.value,
            "AVcontent": avcontentid,
            'AVstartdetail': json.dumps(start, cls=JSONEncoder),
            'AVcontentdetail': json.dumps(content, cls=JSONEncoder),
        })

        with self.sapproval.auto_commit() as s:

            if applyfrom == ApplyFrom.supplizer.value:
                sup = Supplizer.query.filter_by_(SUid=startid).first()
                name = getattr(sup, 'SUname', '')
            elif applyfrom == ApplyFrom.platform.value:
                admin = Admin.query.filter_by_(ADid=startid).first()
                name = getattr(admin, 'ADname', '')
            else:
                user = User.query.filter_by_(USid=startid).first()
                name = getattr(user, 'USname', '')

            aninstance = ApprovalNotes.create({
                "ANid": str(uuid.uuid1()),
                "AVid": av.AVid,
                "ADid": startid,
                "ANaction": ApprovalAction.submit.value,
                "AVadname": name,
                "ANabo": "发起申请",
                "ANfrom": applyfrom
            })
            s.add(av)
            s.add(aninstance)
        return av.AVid

    def __get_category(self, pcid, pclist=None):
        # 所有分类
        if not pclist:
            pclist = []
        if not pcid:
            return pclist
        pc = ProductCategory.query.filter_by_(PCid=pcid).first()
        # pc_list = []
        if not pc:
            return pclist
        pclist.append(pc.PCname)
        return self.__get_category(pc.ParentPCid, pclist)

    def __fill_product_detail(self, product, skuid=None, **kwargs):
        # 填充商品详情
        if not product:
            return

        if isinstance(product.PRattribute, str):
            product.PRattribute = json.loads(product.PRattribute)
        if isinstance(getattr(product, 'PRremarks', None) or '{}', str):
            product.PRremarks = json.loads(getattr(product, 'PRremarks', None) or '{}')
        pb = ProductBrand.query.filter_by_(PBid=product.PBid).first()
        if skuid:
            content = kwargs.get('content')
            skus = ProductSku.query.filter_by_(SKUid=skuid).all()
            product.fill('categorys', ' > '.join(self.__get_category(product.PCid)))
            images = ProductImage.query.filter(
                ProductImage.PRid == product.PRid, ProductImage.isdelete == False).order_by(
                ProductImage.PIsort).all()
            for sku in skus:
                sku.hide('SKUstock')
                sku.fill('skustock', content.SKUstock)
        elif isinstance(product, FreshManFirstProduct):
            fmfs = FreshManFirstSku.query.filter_by_(FMFPid=product.FMFPid).all()
            images = ProductImage.query.filter(
                ProductImage.PRid == product.FMFPid, ProductImage.isdelete == False).order_by(
                ProductImage.PIsort).all()
            skus = []
            for fmf in fmfs:
                sku = ProductSku.query.filter_by_(SKUid=fmf.SKUid).first()
                sku.hide('SKUprice')
                sku.hide('SKUstock')
                sku.fill('skuprice', fmf.SKUprice)
                sku.fill('skustock', fmf.FMFPstock)
                skus.append(sku)
            # skus = ProductSku.query.filter(ProductSku.SKUid == FreshManFirstSku.SKUid)
        else:
            images = ProductImage.query.filter(
                ProductImage.PRid == product.PRid, ProductImage.isdelete == False).order_by(
                ProductImage.PIsort).all()
            product.fill('categorys', ' > '.join(self.__get_category(product.PCid)))
            skus = ProductSku.query.filter_by_(PRid=product.PRid).all()

        product.fill('images', images)

        sku_value_item = []
        for sku in skus:
            if isinstance(sku.SKUattriteDetail, str):
                sku.SKUattriteDetail = json.loads(sku.SKUattriteDetail)
            sku_value_item.append(sku.SKUattriteDetail)

        # sku_value_instance = ProductSkuValue.query.filter_by_({'PRid': product.PRid}).first()
        # if not sku_value_instance:
        sku_value_item_reverse = []
        for index, name in enumerate(product.PRattribute):
            value = list(set([attribute[index] for attribute in sku_value_item]))
            value = sorted(value)
            temp = {
                'name': name,
                'value': value
            }
            sku_value_item_reverse.append(temp)
        # else:
        #     sku_value_item_reverse = []
        #     pskuvalue = sku_value_instance.PSKUvalue
        #     if isinstance(sku_value_instance.PSKUvalue, str):
        #         pskuvalue = json.loads(sku_value_instance.PSKUvalue)
        #     for index, value in enumerate(pskuvalue):
        #         sku_value_item_reverse.append({
        #             'name': product.PRattribute[index],
        #             'value': value
        #         })

        product.fill('SkuValue', sku_value_item_reverse)
        product.fill('brand', pb)
        product.fill('skus', skus)

    def __fill_publish(self, startid, contentid):
        """填充资讯发布"""
        start = User.query.filter_by_(USid=startid).first() or \
                Admin.query.filter_by_(ADid=startid).first() or \
                Supplizer.query.filter_by_(SUid=startid).first()

        content = News.query.filter_by_(NEid=contentid).first()
        if not start or not content:
            return None, None
        return start, content

    def __fill_cash(self, startid, contentid, **kwargs):
        # 填充提现内容
        apply_from = kwargs.get('applyfrom', ApplyFrom.user.value)
        if apply_from == ApplyFrom.user.value:
            start_model = User.query.filter_by_(USid=startid).first()
        elif apply_from == ApplyFrom.supplizer.value:
            start_model = Supplizer.query.filter_by_(SUid=startid).first()
        elif apply_from == ApplyFrom.platform.value:
            start_model = Admin.query.filter(Admin.isdelete == False,
                                             Admin.ADid == startid).first()
        else:
            start_model = None
        content = CashNotes.query.filter_by_(CNid=contentid).first()
        uw = UserWallet.query.filter_by_(USid=startid,
                                         CommisionFor=apply_from).first()
        if not start_model or not content or not uw:
            start_model = None

        content.fill('uWbalance', uw.UWbalance)
        for key in kwargs:
            content.fill(key, kwargs.get(key))

        return start_model, content

    def __fill_settlenment(self, startid, contentid):
        start_model = Supplizer.query.filter(Supplizer.SUid == startid, Supplizer.isdelete == False).first()
        content = SettlenmentApply.query.filter(
            SettlenmentApply.SSAid == contentid, SettlenmentApply.isdelete == False).first()
        uw = UserWallet.query.filter(UserWallet.USid == startid, UserWallet.isdelete == False).first()
        if not start_model or not content:
            return None, None
        ss = SupplizerSettlement.query.filter(
            SupplizerSettlement.SSid == content.SSid, SupplizerSettlement.isdelete == False).first_('结算异常申请数据异常')

        if not uw:

            content.fill('uwtotal', uw.UWtotal or 0)
            content.fill('uwbalance', uw.UWbalance or 0)
            content.fill('uwexpect', uw.UWexpect or 0)
            content.fill('uwcash', uw.UWcash or 0)
        else:
            content.fill('uwtotal', 0)
            content.fill('uwbalance', 0)
            content.fill('uwexpect', 0)
            content.fill('uwcash', 0)
        content.fill('createtime', ss.createtime)
        return start_model, content

    def __fill_agent(self, startid, contentid=None):
        # 填充成为代理商内容
        start_model = User.query.filter_by_(USid=startid).first()
        umfront = UserMedia.query.filter_by_(USid=startid, UMtype=UserMediaType.umfront.value).first()
        umback = UserMedia.query.filter_by_(USid=startid, UMtype=UserMediaType.umback.value).first()
        if not start_model or not umback or not umfront:
            return None, None

        start_model.fill('umfront', umfront['UMurl'])
        start_model.fill('umback', umback['UMurl'])

        return start_model, None

    def __fill_shelves(self, startid, contentid):
        # 填充上架申请
        start_model = Supplizer.query.filter_by_(SUid=startid).first() or \
                      Admin.query.filter_by_(ADid=startid).first()

        content = Products.query.filter_by_(PRid=contentid).first()
        if not start_model or not content:
            return None, None
        self.__fill_product_detail(content)
        return start_model, content

    def __fill_guessnum(self, startid, contentid):
        # done 猜数字
        start_model = Supplizer.query.filter_by_(SUid=startid).first() or Admin.query.filter_by_(ADid=startid).first()
        content = GuessNumAwardApply.query.filter_by_(GNAAid=contentid).first()
        if not start_model or not content:
            return None, None
        product = Products.query.filter_by_(PRid=content.PRid).first()
        self.__fill_product_detail(product, content.SKUid, content=content)
        content.fill('product', product)
        return start_model, content

    def __fill_magicbox(self, startid, contentid):
        # done 魔术礼盒
        start_model = Supplizer.query.filter_by_(SUid=startid).first() or Admin.query.filter_by_(ADid=startid).first()
        content = MagicBoxApply.query.filter_by_(MBAid=contentid).first()
        if not start_model or not content:
            return None, None
        product = Products.query.filter_by_(PRid=content.PRid).first()
        self.__fill_product_detail(product, content.SKUid, content=content)
        content.fill('product', product)
        return start_model, content

    def __fill_trialcommodity(self, startid, contentid):
        # done 使用商品
        start_model = Supplizer.query.filter_by_(SUid=startid).first() or \
                      Admin.query.filter_by_(ADid=startid).first()
        content = TrialCommodity.query.filter_by_(TCid=contentid).first()
        if not start_model or not content:
            return None, None
        # product = TrialCommodity.query.filter_by_(PRid=content.PRid).first()
        content.fill('zh_remarks', "{0}天{1}元".format(content.TCdeadline, int(content.TCdeposit)))
        content.fill('zh_tcstatus', TrialCommodityStatus(content.TCstatus).zh_value)
        prbrand = ProductBrand.query.filter_by_(PBid=content.PBid).first()
        if not prbrand:
            return None, None
        content.fill('brand', prbrand)
        if isinstance(content.TCattribute, str):
            content.TCattribute = json.loads(content.TCattribute)
        content.hide('CreaterId', 'PBid')
        # 商品图片
        image_list = TrialCommodityImage.query.filter_by_(TCid=contentid, isdelete=False).all()
        [image.hide('TCid') for image in image_list]
        content.fill('image', image_list)

        # 填充sku
        skus = TrialCommoditySku.query.filter_by_(TCid=contentid).all()
        sku_value_item = []
        for sku in skus:
            if isinstance(getattr(sku, 'SKUattriteDetail') or '[]', str):
                sku.SKUattriteDetail = json.loads(getattr(sku, 'SKUattriteDetail') or '[]')
            sku.SKUprice = content.TCdeposit
            sku_value_item.append(sku.SKUattriteDetail)
            content.fill('skus', skus)
        # 拼装skuvalue
        sku_value_instance = TrialCommoditySkuValue.query.filter_by_(TCid=contentid).first()
        if not sku_value_instance:
            sku_value_item_reverse = []
            for index, name in enumerate(content.TCattribute):
                value = list(set([attribute[index] for attribute in sku_value_item]))
                value = sorted(value)
                combination = {
                    'name': name,
                    'value': value
                }
                sku_value_item_reverse.append(combination)
        else:
            sku_value_item_reverse = []
            tskuvalue = sku_value_instance.TSKUvalue
            if isinstance(sku_value_instance.TSKUvalue, str):
                tskuvalue = json.loads(sku_value_instance.TSKUvalue)

            for index, value in enumerate(tskuvalue):
                sku_value_item_reverse.append({
                    'name': content.TCattribute[index],
                    'value': value
                })

        content.fill('skuvalue', sku_value_item_reverse)
        return start_model, content

    def __fill_activationcode(self, startid, contentid):
        #
        start_model = User.query.filter_by_(USid=startid).first()
        content = ActivationCodeApply.query.filter_by_(ACAid=contentid).first()
        if not start_model or not content:
            return None, None
        return start_model, content

    def __fill_freshmanfirstproduct(self, startid, contentid):
        # done 新人首单
        start_model = Supplizer.query.filter_by_(SUid=startid).first() or \
                      Admin.query.filter_by_(ADid=startid).first()
        content = FreshManFirstApply.query.filter_by_(FMFAid=contentid).first()
        if not start_model or not content:
            return None, None
        # if apply:
        content.add('createtime')
        content = FreshManFirstProduct.query.filter_by_(FMFAid=contentid).first()
        self.__fill_product_detail(content)
        return start_model, content

    def __fill_approval(self, pt, start, content, **kwargs):
        if pt.PTid == 'tocash':
            return self.__fill_cash(start, content, **kwargs)
        elif pt.PTid == 'toagent':
            return self.__fill_agent(start, content)
        elif pt.PTid == 'toshelves':
            return self.__fill_shelves(start, content)
        elif pt.PTid == 'topublish':
            return self.__fill_publish(start, content)
        elif pt.PTid == 'toguessnum':
            return self.__fill_guessnum(start, content)
        elif pt.PTid == 'tomagicbox':
            return self.__fill_magicbox(start, content)
        elif pt.PTid == 'tofreshmanfirstproduct':
            return self.__fill_freshmanfirstproduct(start, content)
        elif pt.PTid == 'totrialcommodity':
            return self.__fill_trialcommodity(start, content)
        elif pt.PTid == 'toreturn':
            # todo 退货申请目前没有图
            raise ParamsError('退货申请前往订单页面实现')
        elif pt.PTid == 'toactivationcode':
            return self.__fill_activationcode(start, content)
        elif pt.PTid == 'tosettlenment':
            return self.__fill_settlenment(start, content)
        else:
            raise ParamsError('参数异常， 请检查审批类型是否被删除。如果新增了审批类型，请联系开发实现后续逻辑')

    def __get_approvalcontent(self, pt, startid, avcontentid, **kwargs):
        start, content = self.__fill_approval(pt, startid, avcontentid, **kwargs)
        gennerc_log('get start {0} content {1}'.format(start, content))
        if not (start or content):
            raise ParamsError('审批流创建失败，发起人或需审批内容已被删除')
        return start, content


class BaseController:
    @staticmethod
    def get_two_float(f_str, n=2):
        f_str = str(f_str)
        a, b, c = f_str.partition('.')
        c = (c + "0" * n)[:n]
        return Decimal(".".join([a, c]))

    def _commision_preview(self, *args, **kwargs):
        """
        计算最低比例
        :param price:  价格
        :param planet_rate:  平台最低比
        :param planet_and_user_rate: 供应商让利比
        :return:
        """
        price = Decimal(str(kwargs.get('price')))  # 299
        planet_rate = Decimal(str(kwargs.get('planet_rate')))  # 5
        planet_and_user_rate = Decimal(str(kwargs.get('planet_and_user_rate'))) / 100  # 0.2
        current_user_rate = Decimal(str(kwargs.get('current_user_rate'))) / 100  # 0.5
        planet_rate = Decimal(planet_rate) / 100  # 0.05
        user_rate = planet_and_user_rate - planet_rate  # 0.15
        user_commision = price * user_rate  # 给用户的佣金
        current_user_comm = current_user_rate * user_commision
        return self.get_two_float(current_user_comm)
