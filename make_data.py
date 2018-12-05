# -*- coding: utf-8 -*-
from planet import create_app
from planet.config.enums import ItemAuthrity, ItemPostion, ItemType, ActivityType
from planet.extensions.register_ext import db
from planet.models import Items, ProductBrand, Activity


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
        # s_list.append(index_hot_items)

        news_bind_product = Items.create({
            'ITid': 'news_bind_product',
            'ITname': '资讯关联商品',
            'ITdesc': '用于在资讯中进行关联的',
            'ITtype': ItemType.product.value,
            'ITauthority': ItemAuthrity.other.value,
            'ITposition': ItemPostion.news_bind.value
        })
        # s_list.append(news_bind_product)

        news_bind_coupon = Items.create({
            'ITid': 'news_bind_coupon',
            'ITname': '资讯关联优惠券',
            'ITdesc': '用于在资讯中进行关联的',
            'ITtype': ItemType.coupon.value,
            'ITauthority': ItemAuthrity.other.value,
            'ITposition': ItemPostion.news_bind.value
        })
        # s_list.append(news_bind_coupon)

        new_user_items = Items.create({  # 新人推荐标签
            'ITid': 'new_user',
            'ITname': '新人商品',
            'ITdesc': '这是新人才可享受的商品标签',
            'ITtype': ItemType.product.value,
            'ITauthority': ItemAuthrity.new_user.value,
            'ITposition': ItemPostion.new_user_page.value
        })
        # s_list.append(new_user_items)
        index_brands_items = Items.create({
            'ITid': 'index_brand',
            'ITname': '品牌推荐',
            'ITdesc': '这是首页才会出现的品牌推荐',
            'ITtype': ItemType.brand.value,
            'ITposition': ItemPostion.index.value
        })
        # s_list.append(index_brands_items)
        index_brands_product_items = Items.create({
            'ITid': 'index_brand_product',
            'ITname': '品牌推荐商品',
            'ITdesc': '这是首页才会出现的品牌商品',
            'ITposition': ItemPostion.index.value
        })
        # s_list.append(index_brands_product_items)

        index_recommend_product_for_you_items = Items.create({
            'ITid': 'index_recommend_product_for_you',
            'ITname': '首页为您推荐',
            'ITdesc': '首页的为您推荐的商品',
            'ITposition': ItemPostion.index.value
        })

        upgrade_product = Items.create({
            'ITid': 'upgrade_product',
            'ITname': '开店大礼包',
            'ITdesc': '开店大礼包',
            'ITposition': ItemPostion.other.value,
            'ITauthority': ItemPostion.other.value,
        })

        # s_list.append(guess_num_award)
        # db.session.add_all(s_list)
        s_list.append(upgrade_product)
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


if __name__ == '__main__':
    app = create_app()
    with app.app_context():
        make_items()



