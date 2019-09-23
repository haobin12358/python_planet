import os
import uuid
from datetime import datetime, date
from decimal import Decimal

import json

from flask import current_app, request
from sqlalchemy import false

from planet.config.enums import ApplyStatus, ApprovalAction, ApplyFrom, \
    TrialCommodityStatus, ActivationTypeEnum, TicketsOrderStatus
from planet.common.error_response import ParamsError, StatusError
from planet.extensions.register_ext import db, mp_miniprogram
from planet.models import User, Supplizer, Admin, PermissionType, News, Approval, ApprovalNotes, CashNotes, \
    UserWallet, Products, ActivationCodeApply, TrialCommoditySkuValue, TrialCommodityImage, \
    TrialCommoditySku, ProductBrand, TrialCommodity, FreshManFirstProduct, ProductSku, FreshManFirstSku, \
    FreshManFirstApply, MagicBoxApply, GuessNumAwardApply, ProductCategory, SettlenmentApply, \
    SupplizerSettlement, ProductImage, GuessNumAwardProduct, GuessNumAwardSku, TimeLimitedProduct, TimeLimitedActivity, \
    TimeLimitedSku, IntegralProduct, IntegralProductSku, NewsAward, AdminActions, GroupGoodsProduct, Toilet, Guide, \
    ActivationType, Activation, Ticket, TicketsOrder, TicketsOrderActivation

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


class BASEADMIN():
    def create_action(self, AAaction, AAmodel, AAkey):
        detail = request.detail
        detail['data'] = detail['data'].decode()

        admin_action = {
            'AAid': str(uuid.uuid1()),
            'ADid': request.user.id,
            'AAaction': AAaction,
            'AAmodel': AAmodel,
            'AAdetail': json.dumps(detail),
            'AAkey': AAkey
        }
        aa_instance = AdminActions.create(admin_action)
        db.session.add(aa_instance)


class BASEAPPROVAL():
    sapproval = SApproval()

    def create_approval(self, avtype, startid, avcontentid, applyfrom=None, **kwargs):

        current_app.logger.info('start create approval ptid = {0}'.format(avtype))
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
        current_app.logger.info('开始填充商品详情 ')
        if isinstance(product.PRattribute, str):
            product.PRattribute = json.loads(product.PRattribute)
        if isinstance(getattr(product, 'PRremarks', None) or '{}', str):
            product.PRremarks = json.loads(getattr(product, 'PRremarks', None) or '{}')
        pb = ProductBrand.query.filter_by_(PBid=product.PBid).first()
        if skuid:
            content = kwargs.get('content')
            skus = ProductSku.query.filter_by_(SKUid=skuid).all()
            product.fill('categorys', ' > '.join(self.__get_category(product.PCid)))

            for sku in skus:
                sku.hide('SKUstock')
                sku.fill('skustock', content.SKUstock)
        elif isinstance(product, FreshManFirstProduct):
            fmfs = FreshManFirstSku.query.filter_by_(FMFPid=product.FMFPid).all()

            skus = []
            for fmf in fmfs:
                sku = ProductSku.query.filter_by_(SKUid=fmf.SKUid).first()
                sku.hide('SKUprice')
                sku.hide('SKUstock')
                sku.fill('skuprice', fmf.SKUprice)
                sku.fill('skustock', fmf.FMFPstock)
                skus.append(sku)
            # skus = ProductSku.query.filter(ProductSku.SKUid == FreshManFirstSku.SKUid)
        elif isinstance(product, GuessNumAwardProduct):
            gnas = GuessNumAwardSku.query.filter_by(GNAPid=product.GNAPid, isdelete=False).all()

            skus = []
            for fmf in gnas:
                sku = ProductSku.query.filter_by_(SKUid=fmf.SKUid).first()
                sku.hide('SKUprice')
                sku.hide('SKUstock')
                sku.fill('skuprice', fmf.SKUprice)
                sku.fill('skustock', fmf.SKUstock)
                sku.fill('SKUdiscountone', fmf.SKUdiscountone)
                sku.fill('SKUdiscounttwo', fmf.SKUdiscounttwo)
                sku.fill('SKUdiscountthree', fmf.SKUdiscountthree)
                sku.fill('SKUdiscountfour', fmf.SKUdiscountfour)
                sku.fill('SKUdiscountfive', fmf.SKUdiscountfive)
                sku.fill('SKUdiscountsix', fmf.SKUdiscountsix)

                skus.append(sku)
        elif isinstance(product, TimeLimitedProduct):
            product.fill('categorys', ' > '.join(self.__get_category(product.PCid)))
            tls = TimeLimitedSku.query.filter_by(TLPid=product.TLPid, isdelete=False).all()

            skus = []
            tlpstock = 0
            for fmf in tls:
                sku = ProductSku.query.filter_by_(SKUid=fmf.SKUid).first()
                sku.hide('SKUprice')
                sku.hide('SKUstock')
                sku.fill('skuprice', fmf.SKUprice)
                sku.fill('skustock', fmf.TLSstock)
                sku.fill('skuid', fmf.SKUid)
                skus.append(sku)
                tlpstock += int(fmf.TLSstock)
            current_app.logger.info('本次申请共计库存 {}'.format(tlpstock))
            product.fill('tlpstock', tlpstock)
        else:
            product.fill('categorys', ' > '.join(self.__get_category(product.PCid)))
            skus = ProductSku.query.filter_by_(PRid=product.PRid).all()

        images = ProductImage.query.filter(
            ProductImage.PRid == product.PRid, ProductImage.isdelete == False).order_by(
            ProductImage.PIsort).all()
        product.fill('images', images)

        sku_value_item = []
        for sku in skus:
            if isinstance(sku.SKUattriteDetail, str):
                sku.SKUattriteDetail = json.loads(sku.SKUattriteDetail)
            sku_value_item.append(sku.SKUattriteDetail)

        sku_value_item_reverse = []
        for index, name in enumerate(product.PRattribute):
            value = list(set([attribute[index] for attribute in sku_value_item]))
            value = sorted(value)
            temp = {
                'name': name,
                'value': value
            }
            sku_value_item_reverse.append(temp)
        product.fill('SkuValue', sku_value_item_reverse)
        product.fill('brand', pb)
        product.fill('skus', skus)
        current_app.logger.info('填充完商品信息')

    def __fill_publish(self, startid, contentid):
        """填充资讯发布"""
        start = User.query.filter_by_(USid=startid).first() or \
                Admin.query.filter_by_(ADid=startid).first() or \
                Supplizer.query.filter_by_(SUid=startid).first()

        content = News.query.filter_by_(NEid=contentid).first()
        if not start or not content:
            return None, None
        return start, content

    def __fill_newsaward(self, startid, contentid):
        start = Admin.query.filter_by_(ADid=startid).first()
        news_award = NewsAward.query.filter_by_(NAid=contentid).first()
        content = News.query.filter_by_(NEid=news_award.NEid).first()
        content.fill('NAid', news_award.NAid)
        content.fill('NAreward', news_award.NAreward)
        if not start or not news_award or not content:
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
        # umfront = UserMedia.query.filter_by_(USid=startid, UMtype=UserMediaType.umfront.value).first()
        # umback = UserMedia.query.filter_by_(USid=startid, UMtype=UserMediaType.umback.value).first()
        # if not start_model or not umback or not umfront:
        #     return None, None
        # start_model.fill('umfront', umfront['UMurl'])
        # start_model.fill('umback', umback['UMurl'])

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
        product = GuessNumAwardProduct.query.filter_by_(GNAAid=contentid).first()
        self.__fill_product_detail(product, content=content)
        content.fill('product', product)
        return start_model, content

    def __fill_magicbox(self, startid, contentid):
        start_model = Supplizer.query.filter_by_(SUid=startid).first() or Admin.query.filter_by_(ADid=startid).first()
        content = MagicBoxApply.query.filter_by_(MBAid=contentid).first()
        fill_gp_child_method = getattr(self, '_fill_mba')
        product = fill_gp_child_method(content)
        return start_model, product

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
        product = FreshManFirstProduct.query.filter_by_(FMFAid=contentid).first()
        self.__fill_product_detail(product)
        content.fill('product', product)
        return start_model, content

    def __fill_timelimited(self, startid, contentid):
        # 限时
        start_model = Supplizer.query.filter_by_(SUid=startid).first() or \
                      Admin.query.filter_by_(ADid=startid).first()
        content = TimeLimitedProduct.query.filter_by(TLPid=contentid, isdelete=False).first()
        tla = TimeLimitedActivity.query.filter_by(TLAid=content.TLAid, isdelete=False).first()
        if not start_model or not content:
            return None, None
        # product = TimeLimitedProduct.query.filter_by_(TLPid=contentid).first()
        product_model = Products.query.filter_by(PRid=content.PRid, isdelete=False).first_('商品已下架')
        content.fill('PBid', product_model.PBid)
        content.fill('PRattribute', product_model.PRattribute)
        content.fill('PRremarks', product_model.PRremarks)
        content.fill('PCid', product_model.PCid)
        content.fill('PRtitle', product_model.PRtitle)
        content.fill('PRmainpic', product_model.PRmainpic)
        content.fill('TlAname', tla.TlAname)
        # content.fill('PRtitle', product_model.PRtitle)
        # content.fill('PRtitle', product_model.PRtitle)
        # product.fill('PBid',product_model.PBid)
        self.__fill_product_detail(content, content=content)
        # content.fill('product', content)
        return start_model, content

    def __fill_integral(self, startid, contentid):
        start_model = Supplizer.query.filter_by_(SUid=startid).first() or Admin.query.filter_by_(ADid=startid).first()
        ip = IntegralProduct.query.filter_by(IPid=contentid, isdelete=False).first()

        product = Products.query.filter(
            Products.PRid == ip.PRid, Products.isdelete == False).first()
        if not product:
            current_app.logger.info('·商品已删除 prid = {}'.format(ip.PRid))
        product.fields = ['PRid', 'PRtitle', 'PRstatus', 'PRmainpic', 'PRattribute', 'PRdesc', 'PRdescription',
                          'PRlinePrice']
        if isinstance(product.PRattribute, str):
            product.PRattribute = json.loads(product.PRattribute)
        if isinstance(getattr(product, 'PRremarks', None) or '{}', str):
            product.PRremarks = json.loads(getattr(product, 'PRremarks', None) or '{}')

        pb = ProductBrand.query.filter_by(PBid=product.PBid, isdelete=False).first()
        pb.fields = ['PBname', 'PBid']

        images = ProductImage.query.filter(
            ProductImage.PRid == product.PRid, ProductImage.isdelete == False).order_by(
            ProductImage.PIsort).all()
        [img.hide('PRid') for img in images]
        product.fill('images', images)
        product.fill('brand', pb)
        ips_list = IntegralProductSku.query.filter_by(IPid=ip.IPid, isdelete=False).all()
        skus = list()
        sku_value_item = list()
        for ips in ips_list:
            sku = ProductSku.query.filter_by(SKUid=ips.SKUid, isdelete=False).first()
            if not sku:
                current_app.logger.info('该sku已删除 skuid = {0}'.format(ips.SKUid))
                continue
            sku.hide('SKUstock', 'SkudevideRate', 'PRid', 'SKUid')
            sku.fill('skuprice', ips.SKUprice)
            sku.fill('ipsstock', ips.IPSstock)
            sku.fill('ipsid', ips.IPSid)

            if isinstance(sku.SKUattriteDetail, str):
                sku.SKUattriteDetail = json.loads(sku.SKUattriteDetail)
            sku_value_item.append(sku.SKUattriteDetail)
            skus.append(sku)
        if not skus:
            current_app.logger.info('该申请的商品没有sku prid = {0}'.format(product.PRid))
            return
        product.fill('skus', skus)
        sku_value_item_reverse = []
        for index, name in enumerate(product.PRattribute):
            value = list(set([attribute[index] for attribute in sku_value_item]))
            value = sorted(value)
            temp = {
                'name': name,
                'value': value
            }
            sku_value_item_reverse.append(temp)
        product.fill('skuvalue', sku_value_item_reverse)
        product.fill('ipstatus_zh', ApplyStatus(ip.IPstatus).zh_value)
        product.fill('ipstatus_en', ApplyStatus(ip.IPstatus).name)
        product.fill('ipstatus', ip.IPstatus)
        product.fill('ipprice', ip.IPprice)
        product.fill('iprejectreason', ip.IPrejectReason)
        product.fill('ipsaleVolume', ip.IPsaleVolume)
        product.fill('ipid', ip.IPid)
        product.fill('ipfreight', 0)  # 运费目前默认为0

        return start_model, product

    def __fill_groupgoods(self, startid, contentid):
        start_model = Supplizer.query.filter_by_(SUid=startid).first()
        gp = GroupGoodsProduct.query.filter_by(GPid=contentid, isdelete=False).first()
        fill_gp_child_method = getattr(self, '_fill_gp')
        product = fill_gp_child_method(gp)
        return start_model, product

    def __fill_totoilet(self, startid, contentid):
        start = User.query.filter_by_(USid=startid).first() or \
                Admin.query.filter_by_(ADid=startid).first()
        content = Toilet.query.filter_by_(TOid=contentid).first()
        if not start or not content:
            return None, None
        return start, content

    def __fill_toguide(self, startid, contentid):
        start = User.query.filter_by_(USid=startid).first()
        content = Guide.query.filter_by_(GUid=contentid).first()
        if not start or not content:
            return None, None
        return start, content

    def __fill_approval(self, pt, start, content, **kwargs):
        if pt.PTid == 'tocash':
            return self.__fill_cash(start, content, **kwargs)
        elif pt.PTid == 'toagent':
            return self.__fill_agent(start, content)
        elif pt.PTid == 'toshelves':
            return self.__fill_shelves(start, content)
        elif pt.PTid == 'topublish':
            return self.__fill_publish(start, content)
        elif pt.PTid == 'tonewsaward':
            return self.__fill_newsaward(start, content)
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
        elif pt.PTid == 'totimelimited':
            return self.__fill_timelimited(start, content)
        elif pt.PTid == 'tointegral':
            return self.__fill_integral(start, content)
        elif pt.PTid == 'togroupgoods':
            return self.__fill_groupgoods(start, content)
        elif pt.PTid == 'totoilet':
            return self.__fill_totoilet(start, content)
        elif pt.PTid == 'toguide':
            return self.__fill_toguide(start, content)
        else:
            raise ParamsError('参数异常， 请检查审批类型是否被删除。如果新增了审批类型，请联系开发实现后续逻辑')

    def __get_approvalcontent(self, pt, startid, avcontentid, **kwargs):
        start, content = self.__fill_approval(pt, startid, avcontentid, **kwargs)
        current_app.logger.info('get start {0} content {1}'.format(start, content))
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

    @staticmethod
    def get_user_location(lat, lng, usid, ul=None):
        from planet.common.get_location import GetLocation
        from planet.models.user import UserLocation
        try:
            gl = GetLocation(lat, lng)
            result = gl.result
        except Exception as e:
            current_app.logger.error('解析地址失败 {}'.format(e))
            result = {
                'ULlng': lng,
                'ULlat': lat,
                'ULformattedAddress': '请稍后再试'
            }
        with db.auto_commit():
            if ul:
                ul.update(result)
                db.session.add(ul)
                return ul.ULformattedAddress
            result.setdefault('USid', usid)
            result.setdefault('ULid', str(uuid.uuid1()))
            ul = UserLocation.create(result)
            db.session.add(ul)
        return ul.ULformattedAddress

    def img_check(self, filepath):
        """
        图片校验
        :param filepath: 完整的绝对路径
        :return:
        """
        filesize = os.path.getsize(filepath)
        current_app.logger.info('size {}'.format(filesize))
        if filesize > 1024 * 1024:
            # 图片太大
            from PIL import Image
            img = Image.open(filepath)
            x, y = img.size
            x_ = 750
            y_ = y * (x / x_)
            if y_ > 1000:
                y_ = 1000
            time_now = datetime.now()
            year = str(time_now.year)
            month = str(time_now.month)
            day = str(time_now.day)
            tmp_path = os.path.join(
                current_app.config['BASEDIR'], 'img', 'temp', year, month, day)
            if not os.path.isdir(tmp_path):
                os.makedirs(tmp_path)
            tmp_path = os.path.join(tmp_path, os.path.basename(filepath))
            img.resize((x_, y_), Image.LANCZOS).save(tmp_path)
            filepath = tmp_path
        check_result = mp_miniprogram.img_sec_check(filepath)
        current_app.logger.info(check_result)
        if int(check_result.get('errcode', 1)) != 0:
            current_app.logger.error('傻逼在发黄色图片  usid = {}'.format(getattr(request, 'user').id))
            raise ParamsError('图片存在政治有害等违法违规不当信息')

class BASETICKET():

    def add_activation(self, attid, usid, contentid, atnum=0):
        att = ActivationType.query.filter_by(ATTid=attid).first()
        if not att:
            return
        if str(attid) != ActivationTypeEnum.reward.value:
            atnum = att.ATTnum

        atnum = int(atnum)
        at = Activation.create({
            'ATid': str(uuid.uuid1()),
            'USid': usid,
            'ATTid': attid,
            'ATnum': atnum
        })

        now = datetime.now()

        tso_list = TicketsOrder.query.join(Ticket, Ticket.TIid == TicketsOrder.TIid).filter(
            TicketsOrder.TSOstatus == TicketsOrderStatus.pending.value,
            Ticket.TIstartTime <= now,
            Ticket.TIendTime >= now,
            Ticket.isdelete == false(),
            TicketsOrder.USid == usid,
            TicketsOrder.isdelete == false()).all()
        if not tso_list:
            current_app.logger.info('活动已结束预热，活跃分不获取')
            return

        db.session.add(at)
        for tso in tso_list:
            current_app.logger.info('tso status {}'.format(tso.TSOstatus))
            tso.TSOactivation += atnum
            db.session.add(TicketsOrderActivation.create({
                'TOAid': str(uuid.uuid1()),
                'TSOid': tso.TSOid,
                'ATid': at.ATid,
                'TOAcontent': contentid
            }))
