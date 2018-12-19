# -*- coding: utf-8 -*-
import json
import uuid
from datetime import datetime
from decimal import Decimal

from flask import request, current_app
from sqlalchemy import or_, and_, not_

from planet.common.error_response import NotFound, ParamsError, AuthorityError, StatusError
from planet.common.params_validates import parameter_required
from planet.common.success_response import Success
from planet.common.token_handler import token_required, is_admin, is_shop_keeper, is_tourist, is_supplizer, \
    admin_required
from planet.config.cfgsetting import ConfigSettings
from planet.config.enums import ProductStatus, ProductFrom, UserSearchHistoryType, ItemType, ItemAuthrity, ItemPostion, \
    PermissionType, ApprovalType
from planet.control.BaseControl import BASEAPPROVAL
from planet.extensions.register_ext import db
from planet.models import Products, ProductBrand, ProductItems, ProductSku, ProductImage, Items, UserSearchHistory, \
    SupplizerProduct, ProductScene, Supplizer, ProductSkuValue, ProductCategory, Approval
from planet.service.SProduct import SProducts
from planet.extensions.validates.product import ProductOffshelvesForm, ProductOffshelvesListForm, ProductApplyAgreeForm


class CProducts:
    def __init__(self):
        self.sproduct = SProducts()

    def get_product(self):
        data = parameter_required(('prid',))
        prid = data.get('prid')
        product = self.sproduct.get_product_by_prid(prid)
        if not product:
            return NotFound()
        # 获取商品评价平均分（五颗星：0-10）
        praveragescore = product.PRaverageScore
        if float(praveragescore) > 10:
            praveragescore = 10
        elif float(praveragescore) < 0:
            praveragescore = 0
        else:
            praveragescore = round(praveragescore)
        product.PRaverageScore = praveragescore
        product.fill('fiveaveragescore', praveragescore/2)
        product.fill('prstatus_en', ProductStatus(product.PRstatus).name)
        # product.PRdesc = json.loads(getattr(product, 'PRdesc') or '[]')
        product.PRattribute = json.loads(product.PRattribute)
        product.PRremarks = json.loads(getattr(product, 'PRremarks') or '{}')
        # 顶部图
        images = self.sproduct.get_product_images({'PRid': prid})
        product.fill('images', images)
        # 品牌
        brand = self.sproduct.get_product_brand_one({'PBid': product.PBid}) or {}
        product.fill('brand', brand)
        # sku
        skus = self.sproduct.get_sku({'PRid': prid})
        sku_value_item = []
        for sku in skus:
            sku.SKUattriteDetail = json.loads(sku.SKUattriteDetail)
            sku_value_item.append(sku.SKUattriteDetail)
        product.fill('skus', skus)
        # sku value
        # 是否有skuvalue, 如果没有则自行组装
        sku_value_instance = ProductSkuValue.query.filter_by_({
            'PRid': prid
        }).first()
        if not sku_value_instance:
            sku_value_item_reverse = []
            for index, name in enumerate(product.PRattribute):
                value = list(set([attribute[index] for attribute in sku_value_item]))
                value = sorted(value)
                temp = {
                    'name': name,
                    'value': value
                }
                sku_value_item_reverse.append(temp)
        else:
            sku_value_item_reverse = []
            pskuvalue = json.loads(sku_value_instance.PSKUvalue)
            for index, value in enumerate(pskuvalue):
                sku_value_item_reverse.append({
                    'name': product.PRattribute[index],
                    'value': value
                })
        product.fill('SkuValue', sku_value_item_reverse)
        # product_sku_value = self.sproduct.get_sku_value({'PRid': prid})
        # product_sku_value.PSKUvalue = json.loads(getattr(product_sku_value, 'PSKUvalue', '[]'))
        # product.fill('ProductSkuValue', product_sku_value)
        # 场景
        items = self.sproduct.get_item_list([
            ProductItems.PRid == prid,
            ProductItems.isdelete == False
        ])
        # 月销量
        month_sale_instance = self.sproduct.get_monthsale_value_one({'PRid': prid})
        month_sale_value = getattr(month_sale_instance, 'PMSVnum', 0)
        product.fill('month_sale_value', month_sale_value)
        product.fill('items', items)
        # 预计佣金
        cfg = ConfigSettings()
        level1commision = cfg.get_item('commission', 'level1commision')
        product.fill('profict', float(round(Decimal(product.PRprice) * Decimal(level1commision) / 100, 2)))
        if is_admin() or is_supplizer():
            if product.PCid and product.PCid != 'null':
                product.fill('pcids', self._up_category(product.PCid))
        return Success(data=product)

    def get_produt_list(self):
        data = parameter_required()
        try:
            order, desc_asc = data.get('order_type', 'time|desc').split('|')  # 排序方式
            order_enum = {
                'time': Products.createtime,
                'sale_value': Products.PRsalesValue,
                'price': Products.PRprice,
            }
            assert order in order_enum and desc_asc in ['desc', 'asc'], 'order_type 参数错误'
        except Exception as e:
            raise e
        kw = data.get('kw', '').split() or ['']  # 关键词
        pbid = data.get('pbid')  # 品牌
        # 分类参数
        pcid = data.get('pcid')  # 分类id
        pcid = pcid.split('|') if pcid else []
        pcids = self._sub_category_id(pcid)
        pcids = list(set(pcids))
        itid = data.get('itid')  # 场景下的标签id
        prstatus = data.get('prstatus')
        if not is_admin() and not is_supplizer():
            prstatus = prstatus or 'usual'  # 商品状态
        if prstatus:
            prstatus = getattr(ProductStatus, prstatus).value
        product_order = order_enum.get(order)
        if desc_asc == 'desc':
            order_by = product_order.desc()
        elif desc_asc == 'asc':
            order_by = product_order

        filter_args = [
            Products.PBid == pbid,
            or_(and_(*[Products.PRtitle.contains(x) for x in kw]), and_(*[ProductBrand.PBname.contains(x) for x in kw])),
            Products.PCid.in_(pcids),
            ProductItems.ITid == itid,
            Products.PRstatus == prstatus,
        ]
        # 标签位置和权限筛选
        if not is_admin() and not is_supplizer():
            if not itid:
                itposition = data.get('itposition')
                itauthority = data.get('itauthority')
                if not itposition:  # 位置 标签的未知
                    filter_args.extend([Items.ITposition != ItemPostion.other.value,
                                       Items.ITposition != ItemPostion.new_user_page.value])
                else:
                    filter_args.append(Items.ITposition == int(itposition))
                if not itauthority:
                    filter_args.append(or_(Items.ITauthority == ItemAuthrity.no_limit.value, Items.ITauthority.is_(None)))
                else:
                    filter_args.append(Items.ITauthority == int(itauthority))
        # products = self.sproduct.get_product_list(filter_args, [order_by, ])
        query = Products.query.filter(Products.isdelete == False). \
            outerjoin(
            ProductItems, ProductItems.PRid == Products.PRid
        ).outerjoin(
            ProductBrand, ProductBrand.PBid == Products.PBid
        ).outerjoin(Items, Items.ITid == ProductItems.ITid)
        # 后台的一些筛选条件
        # 供应源筛选
        if is_supplizer():
            current_app.logger.info('供应商查看自己的商品')
            suid = request.user.id

        else:
            suid = data.get('suid')
        if suid and suid != 'planet':
            query = query.join(SupplizerProduct, SupplizerProduct.PRid == Products.PRid)
            filter_args.append(
                SupplizerProduct.SUid == suid
            )
        elif suid:
            query = query.outerjoin(SupplizerProduct, SupplizerProduct.PRid == Products.PRid).filter(
                SupplizerProduct.SUid.is_(None)
            )
        products = query.filter_(*filter_args).\
              order_by(order_by).all_with_page()
        # 填充
        for product in products:
            product.fill('prstatus_en', ProductStatus(product.PRstatus).name)
            product.fill('prstatus_zh', ProductStatus(product.PRstatus).zh_value)
            # 品牌
            brand = self.sproduct.get_product_brand_one({'PBid': product.PBid})
            product.fill('brand', brand)
            product.PRattribute = json.loads(product.PRattribute)
            product.PRremarks = json.loads(getattr(product, 'PRremarks') or '{}')
            # 供应商
            supplizer = Supplizer.query.join(
                SupplizerProduct, SupplizerProduct.SUid == Supplizer.SUid
            ).filter_(
                SupplizerProduct.PRid == product.PRid
            ).first()
            if not supplizer:
                product.fill('supplizer', '平台')
            else:
                product.fill('supplizer', supplizer.SUname)
            # product.PRdesc = json.loads(getattr(product, 'PRdesc') or '[]')
        # 搜索记录表
        if kw != [''] and not is_tourist():
            with self.sproduct.auto_commit() as s:
                instance = UserSearchHistory.create({
                    'USHid': str(uuid.uuid1()),
                    'USid': request.user.id,
                    'USHname': ' '.join(kw)
                })
                s.add(instance)
        return Success(data=products)

    @token_required
    def add_product(self):
        self._can_add_product()
        data = parameter_required((
            'pcid', 'pbid', 'prtitle', 'prprice', 'prattribute',
            'prmainpic', 'prdesc', 'images', 'skus'
        ))
        pbid = data.get('pbid')  # 品牌id
        pcid = data.get('pcid')  # 3级分类id
        images = data.get('images')
        skus = data.get('skus')
        prdescription = data.get('prdescription')  # 简要描述
        product_brand = self.sproduct.get_product_brand_one({'PBid': pbid}, '指定品牌不存在')
        product_category = self.sproduct.get_category_one({'PCid': pcid, 'PCtype': 3}, '指定目录不存在')
        if is_supplizer() and product_brand.SUid == request.user.id:
            raise AuthorityError('仅可添加至指定品牌')
        prstocks = 0
        with self.sproduct.auto_commit() as s:
            session_list = []
            # 商品
            prattribute = data.get('prattribute')
            prid = str(uuid.uuid1())
            prmarks = data.get('prmarks')  # 备注
            if prmarks:
                try:
                    prmarks = json.dumps(prmarks)
                    if not isinstance(prmarks, dict):
                        raise TypeError
                except Exception:
                    pass
            prdesc = data.get('prdesc')
            if prdesc:
                if not isinstance(prdesc, list):
                    raise ParamsError('prdesc 格式不正确')
            # sku
            sku_detail_list = []  # 一个临时的列表, 使用记录的sku_detail来检测sku_value是否符合规范
            for sku in skus:
                skuattritedetail = sku.get('skuattritedetail')
                if not isinstance(skuattritedetail, list) or len(skuattritedetail) != len(prattribute):
                    raise ParamsError('skuattritedetail与prattribute不符')
                sku_detail_list.append(skuattritedetail)
                skuprice = float(sku.get('skuprice'))
                skustock = int(sku.get('skustock'))
                assert skuprice > 0 and skustock > 0, 'sku价格或库存错误'
                prstocks += int(skustock)
                sku_dict = {
                    'SKUid': str(uuid.uuid1()),
                    'PRid': prid,
                    'SKUpic': sku.get('skupic'),
                    'SKUprice': round(skuprice, 2),
                    'SKUstock': int(skustock),
                    'SKUattriteDetail': json.dumps(skuattritedetail)
                }
                sku_instance = ProductSku.create(sku_dict)
                session_list.append(sku_instance)
            # 商品
            product_dict = {
                'PRid': prid,
                'PRtitle': data.get('prtitle'),
                'PRprice': data.get('prprice'),
                'PRlinePrice': data.get('prlinePrice'),
                'PRfreight': data.get('prfreight'),
                'PRstocks': prstocks,
                'PRmainpic': data.get('prmainpic'),
                'PCid': pcid,
                'PBid': pbid,
                'PRdesc': prdesc,
                'PRattribute': json.dumps(prattribute),
                'PRremarks': prmarks,
                'PRfrom': self.product_from,
                'CreaterId': request.user.id,
                'PRstatus': self.prstatus,
                'PRdescription': prdescription  # 描述
            }
            product_instance = Products.create(product_dict)
            session_list.append(product_instance)
            #sku value
            pskuvalue = data.get('pskuvalue')
            if pskuvalue:
                if not isinstance(pskuvalue, list) or len(pskuvalue) != len(prattribute):
                    raise ParamsError('pskuvalue与prattribute不符')
                sku_reverce = []
                for index in range(len(prattribute)):
                    value = list(set([attribute[index] for attribute in sku_detail_list]))
                    sku_reverce.append(value)
                    # 对应位置的列表元素应该相同
                    if set(value) != set(pskuvalue[index]):
                        raise ParamsError('请核对pskuvalue')
                # sku_value表
                sku_value_instance = ProductSkuValue.create({
                    'PSKUid': str(uuid.uuid1()),
                    'PRid': prid,
                    'PSKUvalue': json.dumps(pskuvalue)
                })
                session_list.append(sku_value_instance)
            # images
            for image in images:
                image_dict = {
                    'PIid': str(uuid.uuid1()),
                    'PRid': prid,
                    'PIpic': image.get('pipic'),
                    'PIsort': image.get('pisort'),
                }
                image_instance = ProductImage.create(image_dict)
                session_list.append(image_instance)
            # 场景下的小标签 [{'itid': itid1}, ...]
            items = data.get('items')
            if items:
                for item in items:
                    itid = item.get('itid')
                    item = s.query(Items).filter_by_({'ITid': itid, 'ITtype': ItemType.product.value}).first_('指定标签{}不存在'.format(itid))
                    item_product_dict = {
                        'PIid': str(uuid.uuid1()),
                        'PRid': prid,
                        'ITid': itid
                    }
                    item_product_instance = ProductItems.create(item_product_dict)
                    session_list.append(item_product_instance)
            if is_supplizer():
                # 供应商商品表
                session_list.append(SupplizerProduct.create({
                    'SPid': str(uuid.uuid1()),
                    'PRid': prid,
                    'SUid': request.user.id,
                }))
                # 创建审批
                session_list.append(Approval.create({
                    'AVid': str(uuid.uuid1()),
                    'AVname': 'topublish' + datetime.now().strftime('%Y%m%d%H%M%S'),
                    'AVtype': PermissionType.topublish.value,
                    'AVstartid': request.user.id,
                    'AVstatus': 0,
                    # 'AVlevel': '',
                    'AVcontent': prid
                }))
            s.add_all(session_list)
        return Success('添加成功', {'prid': prid})

    @token_required
    def update_product(self):
        """更新商品"""
        data = parameter_required(('prid', ))
        prid = data.get('prid')
        pbid = data.get('pbid')  # 品牌id
        pcid = data.get('pcid')  # 3级分类id
        images = data.get('images')
        skus = data.get('skus')
        prdescription = data.get('prdescription')
        with self.sproduct.auto_commit() as s:
            session_list = []
            # 商品
            prattribute = data.get('prattribute')
            if prattribute:
                prattribute = json.dumps(prattribute)
            product = s.query(Products).filter_by_({'PRid': prid}).first_('商品不存在')
            prmarks = data.get('prmarks')  # 备注
            if prmarks:
                try:
                    prmarks = json.dumps(prmarks)
                    if not isinstance(prmarks, dict):
                        raise TypeError
                except Exception as e:
                    pass
            if pbid:
                product_brand = self.sproduct.get_product_brand_one({'PBid': pbid}, '指定品牌不存在')
            if pcid:
                product_category = self.sproduct.get_category_one({'PCid': pcid, 'PCtype': 3}, '指定目录不存在')

            # sku, 有skuid为修改, 无skuid为新增
            if skus:
                new_sku = []
                sku_ids = []  # 此时传入的skuid
                prstock = 0
                for sku in skus:
                    skuattritedetail = sku.get('skuattritedetail')
                    if not isinstance(skuattritedetail, list) or len(skuattritedetail) != len(skuattritedetail):
                        raise ParamsError('skuattritedetail与prattribute不符')
                    skuprice = sku.get('skuprice')
                    skustock = sku.get('skustock')
                    assert skuprice > 0 and skustock > 0, 'sku价格或库存错误'
                    # 更新或添加删除
                    if 'skuid' in sku:
                        skuid = sku.get('skuid')
                        sku_ids.append(skuid)
                        sku_instance = s.query(ProductSku).filter_by({'SKUid': skuid}).first_('sku不存在')
                        sku_instance.update({
                            'SKUpic': sku.get('skupic'),
                            'SKUattriteDetail': json.dumps(skuattritedetail),
                            'SKUstock': int(skustock),
                            'SKUsn': data.get('skusn')
                        })
                        session_list.append(sku_instance)
                    else:

                        sku_instance = ProductSku.create({
                            'SKUid': str(uuid.uuid1()),
                            'PRid': prid,
                            'SKUpic': sku.get('skupic'),
                            'SKUprice': round(skuprice, 2),
                            'SKUstock': int(skustock),
                            'SKUattriteDetail': json.dumps(skuattritedetail),
                            # 'isdelete': sku.get('isdelete'),
                            'SKUsn': data.get('skusn')
                        })
                        new_sku.append(sku_instance)
                        session_list.append(sku_instance)
                    prstock += sku_instance.SKUstock
                # 剩下的就是删除
                old_sku = ProductSku.query.filter(
                    ProductSku.isdelete == False,
                    ProductSku.PRid == prid,
                    ProductSku.SKUid.notin_(sku_ids)
                ).delete_(synchronize_session=False)
                current_app.logger.info(
                    '删除了{}个不需要的sku, 更新了{}个sku, 添加了{}个新sku '.format(old_sku, len(sku_ids), len(new_sku)))
                # import ipdb
                # ipdb.set_trace()
                # if old_sku > 10:
                #     raise StatusError('删除过多')

            prdesc = data.get('prdesc')
            product_dict = {
                'PRtitle': data.get('prtitle'),
                'PRprice': data.get('prprice'),
                'PRlinePrice': data.get('prlinePrice'),
                'PRfreight': data.get('prfreight'),
                'PRstocks': prstock,
                'PRmainpic': data.get('prmainpic'),
                'PCid': pcid,
                'PBid': pbid,
                'PRdesc': prdesc,
                'PRattribute': prattribute,
                'PRremarks': prmarks,
                'PRdescription': prdescription,

            }
            if product.PRstatus == ProductStatus.sell_out.value:
                product.PRstatus = ProductStatus.usual.value
            product.update(product_dict)
            session_list.append(product)


            # sku value
            pskuvalue = data.get('pskuvalue')
            if pskuvalue:
                if not isinstance(pskuvalue, list) or len(pskuvalue) != len(json.loads(product.PRattribute)):
                    raise ParamsError('pskuvalue与prattribute不符')
                # todo  skudetail校验
                # sku_value表
                exists_sku_value = ProductSkuValue.query.filter_by_({
                    'PRid': prid
                }).first()
                if exists_sku_value:
                    exists_sku_value.update({
                        'PSKUvalue': json.dumps(pskuvalue)
                    })
                    session_list.append(exists_sku_value)
                else:
                    sku_value_instance = ProductSkuValue.create({
                        'PSKUid': str(uuid.uuid1()),
                        'PRid': prid,
                        'PSKUvalue': json.dumps(pskuvalue)
                    })
                    session_list.append(sku_value_instance)
            else:
                """
                sku_value_instance = ProductSkuValue.query.filter_by_({
                    'PRid': prid,
                }).first()
                if sku_value_instance:
                    # 更新sku_value, todo 修改的sku也需要记录
                    old_pskvalue = json.loads(sku_value_instance.PSKUvalue )  # [[联通, 电信], [白, 黑], [16G, 32G]]
                    for o_index, o_value in enumerate(old_pskvalue):
                        for index, value in enumerate(new_sku):
                            if value[o_index] not in old_pskvalue[o_index]:
                                old_pskvalue[o_index].append(value[o_index])
                    # sku_value_instance.PSKUvalue = ''
                    sku_value_instance.PSKUvalue = json.dumps(old_pskvalue)
                    session_list.append(sku_value_instance)
                """
                sku_value_instance = ProductSkuValue.query.filter_by_({
                    'PRid': prid,
                }).first()
                if sku_value_instance:
                    # 默认如果不传就删除原来的, 防止value混乱, todo
                    sku_value_instance.isdelete = True
                    session_list.append(sku_value_instance)

            # images, 有piid为修改, 无piid为新增
            if images:
                piids = []
                new_piids = []
                for image in images:
                    if 'piid' in image:  # 修改
                        piid = image.get('piid')
                        piids.append(piid)
                        image_instance = s.query(ProductImage).filter_by({'PIid': piid}).first_('商品图片信息不存在')
                    else:  # 新增
                        piid = str(uuid.uuid1())
                        image_instance = ProductImage()
                        new_piids.append(piid)
                        image_dict = {
                            'PIid': piid,
                            'PRid': prid,
                            'PIpic': image.get('pipic'),
                            'PIsort': image.get('pisort'),
                            'isdelete': image.get('isdelete')
                        }
                        image_instance.update(image_dict)
                    # [setattr(image_instance, k, v) for k, v in image_dict.items() if v is not None]
                    session_list.append(image_instance)
                # 删除其他
                delete_images = ProductImage.query.filter(
                    ProductImage.isdelete == False,
                    ProductImage.PIid.notin_(piids),
                    ProductImage.PRid == prid,
                ).delete_(synchronize_session=False)
                current_app.logger.info('删除了{}个图片, 修改了{}个, 新增了{}个 '.format(delete_images, len(piids),
                                                                           len(new_piids)))

            # 场景下的小标签 [{'itid': itid1}, ...]
            items = data.get('items')
            if items:
                itids = []
                for item in items:
                    itid = item.get('itid')
                    itids.append(itid)
                    item_instance = s.query(Items).filter_by_({'ITid': itid}).first_('指定标签不存在{}'.format(itid))
                    product_item_instance = s.query(ProductItems).join(Items, ProductItems.ITid == Items.ITid).filter_by_({'ITid': itid}).first_()
                    if product_item_instance:
                        piid = product_item_instance.PIid
                        item_product_instance = s.query(ProductItems).filter_by_({'PIid': piid}).first_('piid不存在')
                    else:
                        piid = str(uuid.uuid1())
                        item_product_instance = ProductItems()
                    item_product_dict = {
                        'PIid': piid,
                        'PRid': prid,
                        'ITid': itid,
                        'isdelete': item.get('isdelete')
                    }
                    [setattr(item_product_instance, k, v) for k, v in item_product_dict.items() if v is not None]
                    session_list.append(item_product_instance)
                # 删除不需要的
                current_app.logger.info(itids)
                ProductItems.query.filter(
                    ProductItems.isdelete == False,
                    ProductItems.ITid.notin_(itids),
                    ProductItems.PRid == prid
                ).update({
                    'isdelete': True
                }, synchronize_session=False)
            s.add_all(session_list)
        return Success('更新成功')

    @token_required
    def delete(self):
        data = parameter_required(('prid', ))
        prid = data.get('prid')
        with self.sproduct.auto_commit() as s:
            s.query(Products).filter_by(PRid=prid).delete_()
        return Success('删除成功')

    @admin_required
    def agree_product(self):
        form = ProductApplyAgreeForm().valid_data()
        prids = form.prids.data
        agree = form.agree.data
        anabo = form.anabo.data
        if agree:  # 同意或拒绝
            msg = '已同意'
            value = ProductStatus.usual.value
        else:
            msg = '已拒绝'
            value = ProductStatus.reject.value
        base_approval = BASEAPPROVAL()
        with db.auto_commit():
            for prid in prids:
                # 可以直接同意, todo 后续需改进
                product = Products.query.filter(
                    Products.isdelete == False,
                    Products.PRid == prid,
                    Products.PRstatus == ProductStatus.auditing.value
                ).update({
                    'PRstatus': value
                })
                if not product:
                    continue
                approval = Approval.query.filter(
                    Approval.isdelete == False,
                    Approval.AVcontent == prid,
                ).first()
                if approval:
                    base_approval.update_approval_no_commit(approval, agree, 1, anabo)
            current_app.logger.info('success product count is {}'.format(product))
        return Success(msg)

    @token_required
    def auditing_detail(self):
        """查看审核详情"""
        pass

    @token_required
    def delete_list(self):
        """删除, 供应商只可以删除自己的"""
        if not is_admin() and not is_supplizer():
            raise AuthorityError()
        data = parameter_required(('prids', ))
        prids = data.get('prids') or []
        with db.auto_commit():
            query = Products.query.filter(
                Products.PRid.in_(prids),
            )
            if is_supplizer():
                query.join(SupplizerProduct, SupplizerProduct.PRid == Products.PRid).filter(
                    SupplizerProduct.isdelete == False,
                    SupplizerProduct.SUid == request.user.id,
                )
            query.delete_(synchronize_session=False)

        return Success('删除成功')

    @token_required
    def off_shelves(self):
        """上下架, 包括审核状态, 不使用"""
        if not is_admin() and not is_supplizer():
            raise AuthorityError()
        form = ProductOffshelvesForm().valid_data()
        prid = form.prid.data
        status = form.status.data
        with self.sproduct.auto_commit() as s:
            query = s.query(Products).filter_by_({"PRid": prid})
            if is_supplizer():
                query.join(SupplizerProduct, SupplizerProduct.PRid == Products.PRid).filter(
                    SupplizerProduct.SUid == request.user.id,
                    SupplizerProduct.isdelete == False,
                )
            query.update({
                'PRstatus': status
            })
            if ProductStatus(status).name == 'usual':
                msg = '上架成功'
            else:
                msg = '下架成功'
        return Success(msg)

    @token_required
    def off_shelves_list(self):
        if not is_admin() and not is_supplizer():
            raise AuthorityError()
        form = ProductOffshelvesListForm().valid_data()
        prids = form.prids.data
        status = form.status.data
        with db.auto_commit():
            query = Products.query.filter(
                Products.PRid.in_(prids)
            )
            if is_supplizer():
                query = query.join(SupplizerProduct, SupplizerProduct.PRid == Products.PRid).filter(
                    SupplizerProduct.SUid == request.user.id
                )
            product = query.first_('商品已删除')
            if product.isdelete is True:
                raise StatusError('商品: {}已删除'.format(product.PRtitle))
            if ProductStatus(status).name == 'usual':
                if not product.PCid:
                    raise StatusError('商品: {}未指定分类'.format(product.PRtitle))  # 上架的商品需要有分类
            offs = query.update({
                'PRstatus': status
            }, synchronize_session=False)

            if ProductStatus(status).name == 'usual':
                current_app.logger.info('共上架了{}个商品'.format(offs))
                msg = '上架成功'
            else:
                current_app.logger.info('共下架了{}个商品'.format(offs))
                msg = '下架成功'
        return Success(msg)

    def search_history(self):
        """"搜索历史"""
        if not is_tourist():
            args = parameter_required(('shtype',))
            shtype = args.get('shtype')
            if shtype not in ['product', 'news']:
                raise ParamsError('shtype, 参数错误')
            shtype = getattr(UserSearchHistoryType, shtype, 'product').value
            usid = request.user.id
            search_history = self.sproduct.get_search_history(
                UserSearchHistory.USid == usid,
                UserSearchHistory.USHtype == shtype,
                UserSearchHistory.isdelete == False,
                order=[UserSearchHistory.createtime.desc()]
            )
        else:
            search_history = []
        return Success(data=search_history)

    def del_search_history(self):
        """清空当前搜索历史"""
        if not is_tourist():
            data = parameter_required(('shtype',))
            shtype = data.get('shtype')
            if shtype not in ['product', 'news']:
                raise ParamsError('shtype, 参数错误')
            shtype = getattr(UserSearchHistoryType, shtype, 'product').value
            usid = request.user.id
            with self.sproduct.auto_commit() as s:
                s.query(UserSearchHistory).filter_by({'USid': usid, 'USHtype': shtype}).delete_()
        return Success('删除成功')

    def guess_search(self):
        """推荐搜索"""
        data = parameter_required(('kw', 'shtype'))
        shtype = data.get('shtype')
        if shtype not in ['product', 'news']:
            raise ParamsError('shtype, 参数错误')
        shtype = getattr(UserSearchHistoryType, shtype, 'product').value
        kw = data.get('kw').strip()
        if not kw:
            raise ParamsError()
        search_words = self.sproduct.get_search_history(
            UserSearchHistory.USHtype == shtype,
            UserSearchHistory.USHname.like(kw + '%'),
            order=[UserSearchHistory.createtime.desc()]
        )
        [sw.hide('USid', 'USHid') for sw in search_words]
        return Success(data=search_words)

    def _can_add_product(self):
        if is_admin():
            current_app.logger.info('管理员添加商品')
            self.product_from = ProductFrom.platform.value
            self.prstatus = None
        elif is_supplizer():  # 供应商添加的商品需要审核
            current_app.logger.info('供应商添加商品')
            self.product_from = ProductFrom.supplizer.value
            self.prstatus = ProductStatus.auditing.value
        else:
            raise AuthorityError()

    def _sub_category_id(self, pcid):
        """遍历子分类, 返回id列表"""
        queue = pcid if isinstance(pcid, list) else [pcid]
        pcids = []
        while True:
            if not queue:
                return pcids
            pcid = queue.pop()
            if pcid not in pcids:
                pcids.append(pcid)
                subs = self.sproduct.get_categorys({'ParentPCid': pcid})
                if subs:
                    for sub in subs:
                        pcid = sub.PCid
                        queue.append(pcid)

    def _up_category(self, pcid, pc_list=()):
        """遍历上级分类至一级"""
        pc_list = list(pc_list)
        pc_list.insert(0, pcid)
        category = ProductCategory.query.filter_by({
            'PCid': pcid,
            'isdelete': False,
        }).first()
        if not category.ParentPCid or category in pc_list:
            return pc_list
        return self._up_category(category.ParentPCid, pc_list)



