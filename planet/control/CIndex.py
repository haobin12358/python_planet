# -*- coding: utf-8 -*-
import uuid
import datetime
from flask import request, current_app
from sqlalchemy import extract, distinct, func

from planet.common.error_response import SystemError, ParamsError
from planet.common.params_validates import parameter_required
from planet.common.success_response import Success
from planet.common.token_handler import token_required, admin_required, is_admin
from planet.config.enums import ProductStatus, ProductBrandStatus, AdminActionS
from planet.control.BaseControl import BASEADMIN
from planet.extensions.register_ext import cache, db
from planet.extensions.validates.index import IndexListBannerForm, IndexSetBannerForm, IndexUpdateBannerForm
from planet.models import Items, ProductBrand, BrandWithItems, Products, ProductItems, IndexBanner, \
    HypermarketIndexBanner, Entry, Admin, UserLoginApi
from planet.service.SIndex import SIndex


class CIndex:
    def __init__(self):
        self.sindex = SIndex()

    # @cache.cached(timeout=30, key_prefix='index')
    def brand_recommend(self):
        current_app.logger.info('获取首页信息')
        data = {
            'brands': ProductBrand.query.join(
                BrandWithItems, BrandWithItems.PBid == ProductBrand.PBid
            ).filter(BrandWithItems.ITid == 'index_brand',
                     ProductBrand.isdelete == False,
                     ProductBrand.PBstatus == ProductBrandStatus.upper.value,
                     BrandWithItems.isdelete == False).all(),
            # 'product': self.list_product('index_brand_product'),
            'product': [],  # 改版后有点多余，暂时返回空
            'hot': self.list_product('index_hot', 'all'),
            'recommend_for_you': self.list_product('index_recommend_product_for_you', 'all_with_page'),
        }
        return Success(data=data)

    # @cache.cached(timeout=30, key_prefix='index_banner')
    def list_banner(self):
        form = IndexListBannerForm().valid_data()
        ibshow = dict(form.ibshow.choices).get(form.ibshow.data)
        index_banners = self.sindex.get_index_banner({'IBshow': ibshow})
        # [index_banner.fill('prtitle', Products.query.filter_by_(PRid=index_banner.PRid).first()['PRtitle'])
        #  for index_banner in index_banners]
        return Success(data=index_banners)

    def visit_num(self):
        uvs = db.session.query(distinct(UserLoginApi.USid)).all()
        today_uv = yesterday_uv = 0
        for uv in uvs:
            is_uv = UserLoginApi.query.filter(
                UserLoginApi.isdelete == False,
                UserLoginApi.USid == str(uv[0]),
                extract('year', UserLoginApi.createtime) == datetime.datetime.now().year,
                extract('month', UserLoginApi.createtime) == datetime.datetime.now().month,
                extract('day', UserLoginApi.createtime) <= datetime.datetime.now().day,
                extract('day', UserLoginApi.createtime) >= datetime.datetime.now().day - 1,
            ).order_by(
                UserLoginApi.createtime.desc()
            ).first()
            if is_uv.createtime.day == datetime.datetime.now().day:
                today_uv = today_uv + 1
            else:
                yesterday_uv = yesterday_uv + 1
        ips = db.session.query(distinct(UserLoginApi.USTip)).all()
        today_ip = yesterday_ip = 0
        for ip in ips:
            is_ip = UserLoginApi.query.distinct(UserLoginApi.USTip).filter(
                UserLoginApi.isdelete == False,
                UserLoginApi.USTip == str(ip[0]),
                extract('year', UserLoginApi.createtime) == datetime.datetime.now().year,
                extract('month', UserLoginApi.createtime) == datetime.datetime.now().month,
                extract('day', UserLoginApi.createtime) <= datetime.datetime.now().day,
                extract('day', UserLoginApi.createtime) >= datetime.datetime.now().day - 1,
            ).order_by(
                UserLoginApi.createtime.desc()
            ).first()
            if is_ip.createtime.day == datetime.datetime.now().day:
                today_ip = today_ip + 1
            else:
                yesterday_ip = yesterday_ip + 1

        current_app.logger.info('uv:{}{} ip:{}{} '.format(today_uv, yesterday_uv, today_ip, yesterday_ip))
        visitnum = {
            'today_visitnum': today_uv,
            'yesterday_visitnum': yesterday_uv,
            'today_ip': today_ip,
            'yesterday_ip': yesterday_ip
        }
        return Success(data=visitnum)

    @admin_required
    def set_banner(self):
        current_app.logger.info("Admin {} set index banner".format(request.user.username))
        form = IndexSetBannerForm().valid_data()
        ibid = str(uuid.uuid1())
        with db.auto_commit():
            banner = IndexBanner.create({
                'IBid': ibid,
                'contentlink': form.contentlink.data,
                'IBpic': form.ibpic.data,
                'IBsort': form.ibsort.data,
                'IBshow': form.ibshow.data
            })
            db.session.add(banner)
            BASEADMIN().create_action(AdminActionS.insert.value, 'IndexBanner', ibid)
        return Success('添加成功', {'ibid': ibid})

    @admin_required
    def update_banner(self):
        current_app.logger.info("Admin {} update index banner".format(request.user.username))
        form = IndexUpdateBannerForm().valid_data()
        ibid = form.ibid.data
        isdelete = form.isdelete.data
        IndexBanner.query.filter_by_(IBid=ibid).first_('未找到该轮播图信息')
        with db.auto_commit():
            banner_dict = {'IBid': ibid,
                           'contentlink': form.contentlink.data,
                           'IBpic': form.ibpic.data,
                           'IBsort': form.ibsort.data,
                           'IBshow': form.ibshow.data,
                           'isdelete': isdelete
                           }
            banner_dict = {k: v for k, v in banner_dict.items() if v is not None}
            banner = IndexBanner.query.filter_by_(IBid=ibid).update(banner_dict)
            BASEADMIN().create_action(AdminActionS.update.value, 'IndexBanner', ibid)
            if not banner:
                raise SystemError('服务器繁忙 10000')
        return Success('修改成功', {'ibid': ibid})

    def list_product(self, itid, pg='all'):
        products = Products.query.join(
            ProductItems, Products.PRid == ProductItems.PRid
        ).filter_(ProductItems.ITid == itid,
                  Products.isdelete == False,
                  ProductItems.isdelete == False,
                  ProductBrand.PBid == Products.PBid,
                  ProductBrand.isdelete == False,
                  Products.PRstatus == ProductStatus.usual.value,
                  Products.isdelete == False
                  ).order_by(ProductItems.createtime.desc(), Products.createtime.desc())
        if pg == 'all':
            products = products.all()
        elif pg == 'all_with_page':
            products = products.all_with_page()
        else:
            products = products.all()
        for product in products:
            brand = ProductBrand.query.filter_by_({'PBid': product.PBid}).first()
            if not brand:
                continue
            product.fields = ['PRid', 'PRtitle', 'PRprice', 'PRlinePrice', 'PRfreight', 'PRstocks', 'PRmainpic',
                              'PBid', 'PRlinePrice']
            product.fill('brand', brand)
            product.fill('pblogo', brand['PBlogo'])
        return products

    @token_required
    def set_hot(self):
        pass

    def list_hypermarket_banner(self):
        filter_args = {
            HypermarketIndexBanner.isdelete == False
        }
        if is_admin():
            data = parameter_required()
            hibshow = data.get('hibshow', None)

            if hibshow is not None and str(hibshow) != 'all':
                filter_args.add(HypermarketIndexBanner.HIBshow == bool(hibshow))
        else:
            filter_args.add(HypermarketIndexBanner.HIBshow == True)

        index_banners = HypermarketIndexBanner.query.filter(*filter_args).order_by(
            HypermarketIndexBanner.HIBsort.asc(), HypermarketIndexBanner.createtime.desc()).all()

        return Success(data=index_banners)

    @admin_required
    def set_hypermarket_banner(self):
        current_app.logger.info("Admin {} set index banner".format(request.user.username))
        # data = parameter_required(('contentlink', 'hibpic', 'hibshow'))
        data = parameter_required()

        ibid = data.get('hibid') or str(uuid.uuid1())

        with db.auto_commit():
            hib = HypermarketIndexBanner.query.filter(
                HypermarketIndexBanner.isdelete == False, HypermarketIndexBanner.HIBid == ibid).first()
            if data.get('delete'):
                if not hib:
                    raise ParamsError('banner 已删除')
                hib.update({'isdelete': True})
                db.session.add(hib)
                return Success('删除成功', {'hibid': ibid})

            hibsort = self._check_sort(data.get('hibsort'))
            hib_dict = {
                'contentlink': data.get('contentlink'),
                'HIBpic': data.get('hibpic'),
                'HIBsort': hibsort,
                'HIBshow': bool(data.get('hibshow'))
            }
            if not hib:
                hib_dict.setdefault('HIBid', ibid)
                hib = HypermarketIndexBanner.create(hib_dict)
                BASEADMIN().create_action(AdminActionS.insert.value, 'HypermarketIndexBanner', ibid)
                msg = '添加成功'
            else:
                hib.update(hib_dict)
                BASEADMIN().create_action(AdminActionS.update.value, 'HypermarketIndexBanner', ibid)
                msg = '修改成功'
            db.session.add(hib)

        return Success(msg, {'hibid': ibid})

    def _check_sort(self, sort_num):
        if not sort_num:
            return 1
        sort_num = int(sort_num)
        count_pc = HypermarketIndexBanner.query.count()
        if sort_num < 1:
            return 1
        if sort_num > count_pc:
            return count_pc
        return sort_num

    def get_entry(self):
        data = parameter_required()
        # entype = data.get('entype', 0)

        filter_args = {Entry.isdelete == False}
        if not is_admin():
            filter_args.add(Entry.ENshow == True)
            # filter_args.add(Entry.ENtype == entype)

        en = Entry.query.filter(*filter_args).order_by(
            Entry.ENshow.desc(), Entry.ENtype.asc(), Entry.createtime.desc()).all()
        for e in en:
            e.hide('ACid')
            if is_admin():
                admin = Admin.query.filter(Admin.ADid == e.ACid, Admin.isdelete == False).first()
                adname = admin.ADname if admin else '平台'
                e.fill('ADname', adname)
            # else:
            # return Success(data=e)

        return Success(data=en)

    @admin_required
    def set_entry(self):
        current_app.logger.info("Admin {} set entry banner".format(request.user.username))
        data = parameter_required(('contentlink', 'enpic', 'enshow'))
        enid = data.get('enid') or str(uuid.uuid1())

        with db.auto_commit():
            en = Entry.query.filter(
                Entry.isdelete == False, Entry.ENid == enid).first()
            if data.get('delete'):
                if not en:
                    raise ParamsError('banner 已删除')
                en.update({'isdelete': True})
                db.session.add(en)
                BASEADMIN().create_action(AdminActionS.delete.value, 'Entry', enid)
                return Success('删除成功', {'enid': enid})

            endict = {
                'contentlink': data.get('contentlink'),
                'ENpic': data.get('enpic'),
                'ENshow': bool(data.get('enshow')),
                'ENtype': data.get('entype')
            }
            if not en:
                endict.setdefault('ENid', enid)
                endict.setdefault('ACid', request.user.id)
                en = Entry.create(endict)
                BASEADMIN().create_action(AdminActionS.insert.value, 'Entry', enid)
                msg = '添加成功'
            else:
                en.update(endict)
                BASEADMIN().create_action(AdminActionS.update.value, 'Entry', enid)
                msg = '修改成功'
            db.session.add(en)

            if en.ENshow:
                Entry.query.filter(
                    Entry.ENid != enid, Entry.isdelete == False, Entry.ENtype == en.ENtype).update({'ENshow': False})
        return Success(msg, {'enid': enid})
