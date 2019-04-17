# -*- coding: utf-8 -*-
import json
from decimal import Decimal

from flask import current_app
import uuid
from planet import create_app
from planet.config.enums import ItemAuthrity, ItemPostion, ItemType, ActivityType
from planet.control.CExcel import CExcel
from planet.extensions.register_ext import db
from planet.models import Items, ProductBrand, Activity, PermissionType, Approval, ProductSku, Admin, Products, User, \
    UserCollection, News


# 添加一些默认的数据
def make_items():
    with db.auto_commit():
        s_list = []
        index_hot_items = Items.create({  # 人气热卖标签
            'ITid': 'index_hot',  # id为'index'
            'ITname': '人气热卖',
            'ITdesc': '这是首页的人气热卖',
            'ITtype': ItemType.product.value,
            'ITauthority': ItemAuthrity.no_limit.value,
            'ITposition': ItemPostion.index.value
        })
        s_list.append(index_hot_items)

        news_product_evaluation = Items.create({
            'ITid': 'product_evaluation',
            'ITname': '商品评测',
            'ITsort': 1,
            'ITdesc': '圈子默认标签',
            'ITtype': ItemType.news.value,
            'ITauthority': ItemAuthrity.no_limit.value,
        })
        s_list.append(news_product_evaluation)

        # 暂时不需要这两类了
        # news_bind_product = Items.create({
        #     'ITid': 'news_bind_product',
        #     'ITname': '资讯关联商品',
        #     'ITdesc': '用于在资讯中进行关联的',
        #     'ITtype': ItemType.product.value,
        #     'ITauthority': ItemAuthrity.other.value,
        #     'ITposition': ItemPostion.news_bind.value
        # })
        # s_list.append(news_bind_product)
        #
        # news_bind_coupon = Items.create({
        #     'ITid': 'news_bind_coupon',
        #     'ITname': '资讯关联优惠券',
        #     'ITdesc': '用于在资讯中进行关联的',
        #     'ITtype': ItemType.coupon.value,
        #     'ITauthority': ItemAuthrity.other.value,
        #     'ITposition': ItemPostion.news_bind.value
        # })
        # s_list.append(news_bind_coupon)

        index_brands_items = Items.create({
            'ITid': 'index_brand',
            'ITname': '品牌推荐',
            'ITdesc': '这是首页才会出现的品牌推荐',
            'ITtype': ItemType.brand.value,
            'ITposition': ItemPostion.index.value
        })
        s_list.append(index_brands_items)
        index_brands_product_items = Items.create({
            'ITid': 'index_brand_product',
            'ITname': '品牌推荐商品',
            'ITdesc': '这是首页才会出现的品牌商品',
            'ITposition': ItemPostion.index.value
        })
        s_list.append(index_brands_product_items)

        index_recommend_product_for_you_items = Items.create({
            'ITid': 'index_recommend_product_for_you',
            'ITname': '首页为您推荐',
            'ITdesc': '首页的为您推荐的商品',
            'ITposition': ItemPostion.index.value
        })
        s_list.append(index_recommend_product_for_you_items)

        upgrade_product = Items.create({
            'ITid': 'upgrade_product',
            'ITname': '开店大礼包',
            'ITdesc': '开店大礼包',
            'ITposition': ItemPostion.other.value,
            'ITauthority': ItemAuthrity.other.value,
        })
        s_list.append(upgrade_product)

        planet_featured = Items.create({
            'ITid': 'planet_featured',
            'ITname': '大行星精选',
            'ITdesc': '场景推荐页下固定的大行星精选',
            'ITsort': -1,
            'ITposition': ItemPostion.index.value,
            'ITauthority': ItemAuthrity.admin_only.value,
        })
        s_list.append(planet_featured)

        db.session.add_all(s_list)


def make_acvitity():
    with db.auto_commit():
        fresh = Activity.create({
            'ACid': 0,
            'ACbackGround': '/img/temp/2018/11/29/3hio8z3JgZWyGx8MP8Szanonymous.jpg_548x600.jpg',
            'ACtopPic': '/img/temp/2018/11/29/4v815Zfzq3tXvVETkdt3anonymous.jpg_1076x500.jpg',
            'ACbutton': '首单可免',
            'ACtype': ActivityType.fresh_man.value,
            'ACdesc': '分享给好友购买, 可返原价, 享受优惠',
            'ACname': '新人首单',
            'ACsort': 0
        })

        db.session.add(fresh)
        guess = Activity.create({
            'ACid': 1,
            'ACbackGround': '/img/temp/2018/11/29/yxEMJIVoarojTCFZv5Qwanonymous.jpg_575x432.jpg',
            'ACtopPic': '/img/temp/2018/11/29/4v815Zfzq3tXvVETkdt3anonymous.jpg_1076x500.jpg',
            'ACbutton': '参与竞猜',
            'ACtype': ActivityType.guess_num.value,
            'ACdesc': '分享给好友购买, 可返原价, 享受优惠',
            'ACname': '新人首单',
            'ACsort': 1
        })
        db.session.add(guess)
        magic = Activity.create({
            'ACid': 2,
            'ACbackGround': '/img/temp/2018/11/29/6qEKBbcPEd3yXyLq2r6hanonymous.jpg_1024x1024.jpg',
            'ACtopPic': '/img/temp/2018/11/29/4v815Zfzq3tXvVETkdt3anonymous.jpg_1076x500.jpg',
            'ACbutton': '邀请好友帮拆礼盒',
            'ACtype': ActivityType.magic_box.value,
            'ACname': '魔术礼盒',
            'ACsort': 2
        })
        db.session.add(magic)

        free = Activity.create({
            'ACid': 3,
            'ACbackGround': '/img/temp/2018/11/29/6qEKBbcPEd3yXyLq2r6hanonymous.jpg_1024x1024.jpg',
            'ACtopPic': '/img/temp/2018/11/29/4v815Zfzq3tXvVETkdt3anonymous.jpg_1076x500.jpg',
            'ACbutton': '我要试用',
            'ACtype': ActivityType.free_use.value,
            'ACname': '试用商品',
            'ACsort': 3
        })
        db.session.add(free)


def make_permissiontype():
    with db.auto_commit():
        toagent = PermissionType.create({
            'PTid': 'toagent',
            'PTname': '代理商申请',
            'PTmodelName': 'User'
        })
        db.session.add(toagent)

        tocash = PermissionType.create({
            'PTid': 'tocash',
            'PTname': '提现申请',
            'PTmodelName': 'CashNotes'
        })
        db.session.add(tocash)
        toshelves = PermissionType.create({
            'PTid': 'toshelves',
            'PTname': '商品上架申请',
            'PTmodelName': 'Products'
        })
        db.session.add(toshelves)
        topublish = PermissionType.create({
            'PTid': 'topublish',
            'PTname': '资讯发布申请',
            'PTmodelName': 'News'
        })
        db.session.add(topublish)
        toguessnum = PermissionType.create({
            'PTid': 'toguessnum',
            'PTname': '猜数字活动申请',
            'PTmodelName': 'GuessNumAwardApply'
        })
        db.session.add(toguessnum)
        tomagicbox = PermissionType.create({
            'PTid': 'tomagicbox',
            'PTname': '魔盒活动申请',
            'PTmodelName': 'MagicBoxApply'
        })
        db.session.add(tomagicbox)
        tofreshmanfirstproduct = PermissionType.create({
            'PTid': 'tofreshmanfirstproduct',
            'PTname': '新人首单商品活动申请',
            'PTmodelName': 'FreshManFirstApply'
        })
        db.session.add(tofreshmanfirstproduct)
        totrialcommodity = PermissionType.create({
            'PTid': 'totrialcommodity',
            'PTname': '试用商品上架申请',
            'PTmodelName': 'TrialCommodity'
        })
        db.session.add(totrialcommodity)
        toreturn = PermissionType.create({
            'PTid': 'toreturn',
            'PTname': '退货审请',
            'PTmodelName': 'TrialCommodity'
        })
        db.session.add(toreturn)
        toactivationcode = PermissionType.create({
            'PTid': 'toactivationcode',
            'PTname': '激活码购买申请',
            'PTmodelName': 'ActivationCodeApply'
        })
        db.session.add(toactivationcode)
        tosettlenment = PermissionType.create({
            'PTid': 'tosettlenment',
            'PTname': '供应商结算异常申请',
            'PTmodelName': 'SettlenmentApply'
        })
        db.session.add(tosettlenment)


def make_admin():
    with db.auto_commit():
        from werkzeug.security import generate_password_hash
        db.session.add(Admin.create({
            'ADid': 'adid1',
            'ADnum': 100001,
            'ADname': '管理员',
            'ADtelphone': '13588046135',
            'ADpassword': generate_password_hash('12345'),
            'ADfirstname': '管理员',
            'ADheader': '/img/defaulthead/2018/11/28/db7067a8-f2d0-11e8-80bc-00163e08d30f.png',
            'ADlevel': 1,
        }))


def add_product_promotion():
    with db.auto_commit():
        product_list = Products.query.filter(Products.isdelete == False).all()
        for product in product_list:
            if not product.PRpromotion:
                from planet.common.assemble_picture import AssemblePicture
                assemble = AssemblePicture(
                    product.PRid, product.PRtitle, product.PRprice, product.PRlinePrice, product.PRmainpic)

                product.PRpromotion = assemble.assemble()


def check_abnormal_sale_volume():
    """销量修正"""
    with db.auto_commit():
        from planet.models import OrderPart, OrderMain, ProductMonthSaleValue
        from sqlalchemy import extract
        from sqlalchemy import func

        product_list = Products.query.filter(Products.PRsalesValue != 0, Products.isdelete == False).all()
        for product in product_list:
            opcount = OrderPart.query.outerjoin(OrderMain, OrderMain.OMid == OrderPart.OMid
                                                ).filter(OrderMain.isdelete == False,
                                                         OrderPart.isdelete == False,
                                                         OrderMain.OMstatus != -40,
                                                         OrderPart.PRid == product.PRid,
                                                         OrderPart.OPisinORA == False).count()
            print('当前PRid: {}, 销量数为{}, 订单count{}'.format(product.PRid, product.PRsalesValue, opcount))
            current_app.logger.info('当前PRid: {}, 销量数为{}, 订单count{}'.format(product.PRid, product.PRsalesValue, opcount))
            # 修正商品销量
            product.update({'PRsalesValue': opcount}, null='no')
            db.session.add(product)
            # 修正商品月销量
            ops = db.session.query(extract('month', OrderPart.createtime), func.count('*')).outerjoin(OrderMain,
                                                                                                      OrderMain.OMid == OrderPart.OMid
                                                                                                      ).filter(
                OrderMain.isdelete == False,
                OrderPart.isdelete == False,
                OrderMain.OMstatus != -40,
                OrderPart.PRid == product.PRid,
                OrderPart.OPisinORA == False
                ).group_by(
                extract('month', OrderPart.createtime)).order_by(extract('month', OrderPart.createtime).asc()).all()
            for o in ops:
                # print(o)
                print("该商品{}月份销量为{}".format(o[0], o[-1]))
                current_app.logger.info("该商品{}月份销量为{}".format(o[0], o[-1]))
                ProductMonthSaleValue.query.filter(
                    ProductMonthSaleValue.PRid == product.PRid,
                    ProductMonthSaleValue.isdelete == False,
                    extract('year', ProductMonthSaleValue.createtime) == 2019,
                    extract('month', ProductMonthSaleValue.createtime) == o[0],
                ).update({
                    'PMSVnum': o[-1],
                }, synchronize_session=False)

            # ops = db.session.query(OrderPart).outerjoin(OrderMain,
            #                                             OrderMain.OMid == OrderPart.OMid
            #                                             ).filter(OrderMain.isdelete == False,
            #                                                      OrderPart.isdelete == False,
            #                                                      OrderMain.OMstatus != -40,
            #                                                      OrderPart.PRid == product.PRid,
            #                                                      OrderPart.OPisinORA == False
            #                                                      ).order_by(OrderPart.createtime.desc()).all()
            # march_sale_volume = 0
            # april_sale_volume = 0
            # for op in ops:
            #     if op.createtime.month == 3:
            #         march_sale_volume += 1
            #     elif op.createtime.month == 4:
            #         april_sale_volume += 1
            # print(ops)

            # print("该商品三月销量为{} ， 四月销量为{}".format(march_sale_volume, april_sale_volume))
            # 修正月销量
            # ProductMonthSaleValue.query.filter(
            #     ProductMonthSaleValue.PRid == product.PRid,
            #     ProductMonthSaleValue.isdelete == False,
            #     extract('year', ProductMonthSaleValue.createtime) == 2018,
            #     extract('month', ProductMonthSaleValue.createtime) == 3,
            # ).update({
            #     'PMSVnum': march_sale_volume,
            # }, synchronize_session=False)
            # ProductMonthSaleValue.query.filter(
            #     ProductMonthSaleValue.PRid == product.PRid,
            #     ProductMonthSaleValue.isdelete == False,
            #     extract('year', ProductMonthSaleValue.createtime) == 2018,
            #     extract('month', ProductMonthSaleValue.createtime) == 4,
            # ).update({
            #     'PMSVnum': april_sale_volume,
            # }, synchronize_session=False)


if __name__ == '__main__':
    app = create_app()
    with app.app_context():
        # admin = PermissionType.query.first_()
        # admin_str = json.dumps(admin, cls=JSONEncoder)
        # print(admin.__dict__)
        # print(admin_str)
        # make_acvitity()
        # make_items()
        # make_permissiontype()
        # make_admin()
        # cexcel = CExcel()
        # filepath = r'D:\QQ\微信\file\WeChat Files\wxid_wnsa7sn01tu922\FileStorage\File\2019-03\product_insert.xlsx'
        # filepath = 'C:\Users\刘帅斌\Desktop\product_insert.xlsx'
        # cexcel.insertproduct(filepath)  urllib.request.urlretrieve
        # cexcel._insertproduct(filepath)
        # add_product_promotion()
        # check_abnormal_sale_volume()
        pass
