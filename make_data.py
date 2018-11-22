# -*- coding: utf-8 -*-
from planet import create_app
from planet.config.enums import ItemAuthrity, ItemPostion, ItemType
from planet.extensions.register_ext import db
from planet.models import Items, ProductBrand

# 添加一些默认的数据
app = create_app()
with app.app_context():
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
        new_user_items = Items.create({  # 新人推荐标签
            'ITid': 'new_user',
            'ITname': '新人商品',
            'ITdesc': '这是新人才可享受的商品标签',
            'ITtype': ItemType.product.value,
            'ITauthority': ItemAuthrity.new_user.value,
            'ITposition': ItemPostion.new_user_paga.value
        })
        s_list.append(new_user_items)
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

        db.session.add_all(s_list)


