# -*- coding: utf-8 -*-
import datetime
import json
import uuid
from decimal import Decimal

from flask import current_app
import uuid
from planet import create_app
from planet.config.enums import ItemAuthrity, ItemPostion, ItemType, ActivityType, TimeLimitedStatus
from planet.control.CExcel import CExcel
from planet.extensions.register_ext import db
from planet.models import Items, ProductBrand, Activity, PermissionType, Approval, ProductSku, Admin, Products, \
    TimeLimitedActivity, UserActivationCode, ActivationCodeApply, MakeOver


# 添加一些默认的数据
def make_items():
    with db.auto_commit():
        s_list = []
        # index_hot_items = Items.create({  # 人气热卖标签
        #     'ITid': 'index_hot',  # id为'index'
        #     'ITname': '人气热卖',
        #     'ITdesc': '这是首页的人气热卖',
        #     'ITtype': ItemType.product.value,
        #     'ITauthority': ItemAuthrity.no_limit.value,
        #     'ITposition': ItemPostion.index.value
        # })
        # s_list.append(index_hot_items)
        #
        # news_product_evaluation = Items.create({
        #     'ITid': 'product_evaluation',
        #     'ITname': '商品评测',
        #     'ITsort': 1,
        #     'ITdesc': '圈子默认标签',
        #     'ITtype': ItemType.news.value,
        #     'ITauthority': ItemAuthrity.no_limit.value,
        # })
        # s_list.append(news_product_evaluation)
        #
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

        # index_brands_items = Items.create({
        #     'ITid': 'index_brand',
        #     'ITname': '品牌推荐',
        #     'ITdesc': '这是首页才会出现的品牌推荐',
        #     'ITtype': ItemType.brand.value,
        #     'ITposition': ItemPostion.index.value
        # })
        # s_list.append(index_brands_items)
        # index_brands_product_items = Items.create({
        #     'ITid': 'index_brand_product',
        #     'ITname': '品牌推荐商品',
        #     'ITdesc': '这是首页才会出现的品牌商品',
        #     'ITposition': ItemPostion.index.value
        # })
        # s_list.append(index_brands_product_items)
        #
        # index_recommend_product_for_you_items = Items.create({
        #     'ITid': 'index_recommend_product_for_you',
        #     'ITname': '首页为您推荐',
        #     'ITdesc': '首页的为您推荐的商品',
        #     'ITposition': ItemPostion.index.value
        # })
        # s_list.append(index_recommend_product_for_you_items)
        #
        # upgrade_product = Items.create({
        #     'ITid': 'upgrade_product',
        #     'ITname': '开店大礼包',
        #     'ITdesc': '开店大礼包',
        #     'ITposition': ItemPostion.other.value,
        #     'ITauthority': ItemAuthrity.other.value,
        # })
        # s_list.append(upgrade_product)
        #
        # planet_featured = Items.create({
        #     'ITid': 'planet_featured',
        #     'ITname': '大行星精选',
        #     'ITdesc': '场景推荐页下固定的大行星精选',
        #     'ITsort': -1,
        #     'ITposition': ItemPostion.index.value,
        #     'ITauthority': ItemAuthrity.admin_only.value,
        # })
        # s_list.append(planet_featured)
        home_recommend = Items.create({
            'ITid': 'home_recommend',
            'ITname': '新品推荐',
            'ITdesc': '首页下新品推荐商品',
            'ITposition': ItemPostion.index.value,
            'ITauthority': ItemAuthrity.no_limit.value,
        })
        s_list.append(home_recommend)

        home_recommend_category = Items.create({
            'ITid': 'home_recommend_category',
            'ITname': '优惠券推荐',
            'ITdesc': '首页下推荐优惠券',
            'ITposition': ItemPostion.index.value,
            'ITauthority': ItemAuthrity.no_limit.value,
        })
        s_list.append(home_recommend_category)

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

        timelimit = Activity.create({
            'ACid': 4,
            'ACbackGround': '/img/temp/2018/11/29/6qEKBbcPEd3yXyLq2r6hanonymous.jpg_1024x1024.jpg',
            'ACtopPic': '/img/temp/2018/11/29/4v815Zfzq3tXvVETkdt3anonymous.jpg_1076x500.jpg',
            'ACbutton': '限时特惠',
            'ACtype': ActivityType.time_limited.value,
            'ACname': '限时特惠',
            'ACsort': 4
        })
        db.session.add(timelimit)


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
        tointegral = PermissionType.create({
            'PTid': 'tointegral',
            'PTname': '星币商品申请',
            'PTmodelName': 'IntegralProduct'
        })
        db.session.add(tointegral)


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
            current_app.logger.info('当前PRid: {}, 销量数为{}, 订单count{}'.format(
                product.PRid, product.PRsalesValue, opcount))
            # 修正商品销量
            product.update({'PRsalesValue': opcount}, null='no')
            db.session.add(product)
            # 修正商品月销量
            ops = db.session.query(extract('month', OrderPart.createtime), func.count('*')).outerjoin(
                OrderMain,OrderMain.OMid == OrderPart.OMid).filter(
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


def check_product_from():
    """平台上架供应商商品修正"""
    with db.auto_commit():
        from planet.config.enums import ProductFrom
        from planet.models.product import SupplizerProduct, Supplizer
        products = Products.query.join(ProductBrand, ProductBrand.PBid == Products.PBid
                                       ).filter(Products.PRfrom == ProductFrom.platform.value,
                                                Products.isdelete == False,
                                                ProductBrand.isdelete == False,
                                                ProductBrand.SUid.isnot(None),
                                                ).order_by(Products.createtime.desc()).all()
        old_prid = []
        for pr in products:
            pb = ProductBrand.query.join(Supplizer, Supplizer.SUid == ProductBrand.SUid
                                         ).filter(Supplizer.isdelete == False,
                                                  Supplizer.SUstatus == 0,
                                                  ProductBrand.PBid == pr.PBid,
                                                  ProductBrand.isdelete == False).first()
            if not pb:
                print("品牌供应商状态异常")
                continue
            old_prid.append(pr.PRid)

            if SupplizerProduct.query.filter(SupplizerProduct.SUid == pb.SUid,
                                             SupplizerProduct.PRid == pr.PBid,
                                             SupplizerProduct.isdelete == False
                                             ).first():
                print("该商品存在与供应商商品关联表中")
            else:
                print("该商品不在供应商商品关联表中")

            a = '平台' if str(pr.PRfrom) == '0' else '供应商'
            print("商品名 {} 来源于 {} 关联的品牌是  {} 当前 createID:{} 创建时间为 {}".format(
                pr.PRtitle, a, pb.PBname, pr.CreaterId, pr.createtime))
            # 避免操作错误，暂时注释掉，使用时取消注释
            print("  >>> 开始修改 <<< ")
            pr.update({'PRfrom': 10, 'CreaterId': pb.SUid})
            db.session.add(pr)
            sp_instance = SupplizerProduct.create({
                'SPid': str(uuid.uuid1()),
                'PRid': pr.PRid,
                'SUid': pb.SUid
            })
            db.session.add(sp_instance)
            print("  >>> 修改结束 <<<  ")
        print("共有{}个商品存在来源于平台，但关联了供应商品牌的情况".format(len(products)))
        print("修改的PRids >>> {}".format(old_prid))


def change_tla_status():
    tla_list = TimeLimitedActivity.query.filter(TimeLimitedActivity.isdelete == False).all()
    time_now = datetime.datetime.now()
    with db.auto_commit():
        for tla in tla_list:
            if tla.TLAstartTime > time_now:
                tla.TLAstatus = TimeLimitedStatus.waiting.value
            elif tla.TLAendTime < time_now:
                tla.TLAstatus = TimeLimitedStatus.end.value
            else:
                tla.TLAstatus = TimeLimitedStatus.starting.value


def add_uac_acaid():
    user_act_codes = UserActivationCode.query.filter(
        UserActivationCode.isdelete == False,
    ).all()
    # print(user_act_codes)
    with db.auto_commit():
        cratetime_list = []
        for user_act_code in user_act_codes:

            if user_act_code.ACAid == None:
                createtime = user_act_code.createtime
                # print(createtime)
                cratetime_list.append(createtime)
                createtime1 = createtime + datetime.timedelta(hours=3)
                createtime2 = createtime - datetime.timedelta(hours=3)
                aca = ActivationCodeApply.query.filter(
                    ActivationCodeApply.USid == user_act_code.USid,
                    ActivationCodeApply.updatetime <= createtime1,
                    ActivationCodeApply.updatetime >= createtime2,
                    ActivationCodeApply.isdelete == False
                ).first()
                # print(aca)
                if aca:
                    user_act_code.update({'ACAid': aca.ACAid})
                    db.session.add(user_act_code)
        print({}.fromkeys(cratetime_list).keys())


def init_make_over():
    with db.auto_commit():
        mo = MakeOver.create({
            'Moid': 1,
        })
        db.session.add(mo)


if __name__ == '__main__':
    app = create_app()
    with app.app_context():
        # admin = PermissionType.query.first_()
        # admin_str = json.dumps(admin, cls=JSONEncoder)
        # print(admin.__dict__)
        # print(admin_str)
        # make_acvitity()
        make_items()
        # make_permissiontype()
        # make_admin()
        # cexcel = CExcel()
        # filepath = r'D:\QQ\微信\file\WeChat Files\wxid_wnsa7sn01tu922\FileStorage\File\2019-03\product_insert.xlsx'
        # filepath = 'C:\Users\刘帅斌\Desktop\product_insert.xlsx'
        # cexcel.insertproduct(filepath)  urllib.request.urlretrieve
        # cexcel._insertproduct(filepath)
        # add_product_promotion()
        # check_abnormal_sale_volume()
        # check_product_from()
        # change_tla_status()
        # add_uac_acaid()
        pass
