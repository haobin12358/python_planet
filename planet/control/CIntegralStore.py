import json
import uuid

from flask import request, current_app

from planet.common.error_response import AuthorityError, DumpliError, ParamsError, StatusError
from planet.common.params_validates import parameter_required
from planet.common.success_response import Success
from planet.common.token_handler import is_supplizer, is_admin, common_user, is_tourist, token_required
from planet.config.cfgsetting import ConfigSettings
from planet.config.enums import ApplyFrom, ApplyStatus, ProductStatus, Client, OrderFrom, PayType, UserIntegralAction, \
    UserIntegralType, AdminAction
from planet.control.BaseControl import BASEAPPROVAL, BASEADMIN
from planet.control.COrder import COrder
from planet.extensions.register_ext import db
from planet.models import Admin, Supplizer, IntegralProduct, Products, ProductSku, IntegralProductSku, ProductBrand, \
    ProductImage, Approval, User, OrderPay, OrderMain, UserAddress, AddressArea, AddressCity, AddressProvince, \
    OrderPart, UserIntegral


class CIntegralStore(COrder, BASEAPPROVAL):

    def apply(self):
        """申请添加商品"""

        if is_admin():
            admin = Admin.query.filter_by_(ADid=request.user.id).first_("账号状态错误")
            ipfrom = ApplyFrom.platform.value
            uid = admin.ADid
        # elif is_supplizer():
        #     sup = Supplizer.query.filter_by_(SUid=request.user.id).first_("账号状态错误")
        #     ipfrom = ApplyFrom.supplizer.value
        #     uid = sup.SUid
        else:
            raise AuthorityError()
        data = parameter_required(('prid', 'ipprice', 'skus'))
        prid, ipprice, skus = data.get('prid'), data.get('ipprice', 0), data.get('skus')
        ipprice = self._check_price(ipprice)

        ip = IntegralProduct.query.filter(IntegralProduct.isdelete == False,
                                          IntegralProduct.PRid == prid,
                                          ).first()
        if ip:
            raise DumpliError('该商品申请已存在')
        filter_args = [Products.PRid == prid,
                       Products.isdelete == False,
                       Products.PRstatus == ProductStatus.usual.value]
        if is_supplizer():  # 供应商只能添加自己的
            filter_args.append(Products.PRfrom == ipfrom)
            filter_args.append(Products.CreaterId == uid)
        instance_list = list()
        with db.auto_commit():
            product = Products.query.filter(*filter_args).first_('只能选择自己的商品')
            ip_instance = IntegralProduct.create({
                'IPid': str(uuid.uuid1()),
                'SUid': uid,
                'IPfrom': ipfrom,
                'PRid': prid,
                'IPstatus': ApplyStatus.wait_check.value,
                'IPprice': ipprice
            })
            instance_list.append(ip_instance)
            for sku in skus:
                parameter_required(('skuid', 'skuprice', 'ipsstock'), datafrom=sku)
                skuid, skuprice, ipsstock = sku.get('skuid'), sku.get('skuprice'), sku.get('ipsstock')
                skuprice = self._check_price(skuprice)
                ipsstock = self._check_price(ipsstock)
                sku_instance = ProductSku.query.filter_by(isdelete=False, PRid=product.PRid,
                                                          SKUid=skuid).first_('商品sku信息不存在')
                # 从商品sku中减库存
                super(CIntegralStore, self)._update_stock(-int(ipsstock), product, sku_instance)
                ipsku_instance = IntegralProductSku.create({
                    'IPSid': str(uuid.uuid1()),
                    'IPid': ip_instance.IPid,
                    'IPSstock': ipsstock,
                    'SKUid': skuid,
                    'SKUprice': skuprice
                })
                instance_list.append(ipsku_instance)
            db.session.add_all(instance_list)
            if is_admin():
                BASEADMIN().create_action(AdminAction.insert.value, 'IntegralProduct', str(uuid.uuid1()))
        super(CIntegralStore, self).create_approval('tointegral', uid, ip_instance.IPid, applyfrom=ipfrom)
        return Success('申请成功', data=dict(IPid=ip_instance.IPid))

    def update(self):
        """修改"""
        if is_admin():
            admin = Admin.query.filter_by_(ADid=request.user.id).first_("账号状态错误")
            ipfrom = ApplyFrom.platform.value
            uid = admin.ADid
        # elif is_supplizer():
        #     sup = Supplizer.query.filter_by_(SUid=request.user.id).first_("账号状态错误")
        #     ipfrom = ApplyFrom.supplizer.value
        #     uid = sup.SUid
        else:
            raise AuthorityError()
        data = parameter_required(('ipid', 'ipprice', 'skus'))
        ipid, ipprice, skus = data.get('ipid'), data.get('ipprice', 0), data.get('skus')
        ipprice = self._check_price(ipprice)
        ip = IntegralProduct.query.filter(IntegralProduct.isdelete == False,
                                          IntegralProduct.IPid == ipid,
                                          IntegralProduct.IPstatus.in_([ApplyStatus.cancle.value,
                                                                        ApplyStatus.reject.value,
                                                                        ApplyStatus.shelves.value])
                                          ).first_("当前状态不可进行编辑")
        if ip.SUid != uid:
            raise AuthorityError('仅可编辑自己的商品申请')
        filter_args = [Products.PRid == ip.PRid,
                       Products.isdelete == False,
                       Products.PRstatus == ProductStatus.usual.value]
        if is_supplizer():
            filter_args.append(Products.CreaterId == uid)
        product = Products.query.filter(*filter_args).first_("当前商品状态不允许编辑")
        instance_list = list()
        with db.auto_commit():
            ip_dict = {
                'IPstatus': ApplyStatus.wait_check.value,
                'IPprice': ipprice
            }
            ip.update(ip_dict)
            instance_list.append(ip)

            # 原sku全部删除
            old_ips = IntegralProductSku.query.filter_by_(IPid=ip.IPid).all()
            for old_ipsku in old_ips:
                old_ipsku.isdelete = True
                # super(CIntegralStore, self)._update_stock(int(old_ipsku.IPSstock), skuid=old_ipsku.SKUid)
            # 接收新sku并重新扣除库存
            for sku in skus:
                parameter_required(('skuid', 'skuprice', 'ipsstock'), datafrom=sku)
                skuid, skuprice, ipsstock = sku.get('skuid'), sku.get('skuprice'), sku.get('ipsstock')
                skuprice = self._check_price(skuprice)
                ipsstock = self._check_price(ipsstock)
                sku_instance = ProductSku.query.filter_by(isdelete=False, PRid=ip.PRid,
                                                          SKUid=skuid).first_('商品sku信息不存在')

                # 从商品sku中减库存
                super(CIntegralStore, self)._update_stock(-int(ipsstock), product, sku_instance)
                ipsku_instance = IntegralProductSku.create({
                    'IPSid': str(uuid.uuid1()),
                    'IPid': ip.IPid,
                    'IPSstock': ipsstock,
                    'SKUid': skuid,
                    'SKUprice': skuprice
                })
                instance_list.append(ipsku_instance)
            db.session.add_all(instance_list)
            if is_admin():
                BASEADMIN().create_action(AdminAction.update.value, 'IntegralProduct', str(uuid.uuid1()))
        super(CIntegralStore, self).create_approval('tointegral', uid, ip.IPid, applyfrom=ipfrom)
        return Success('更新成功', data=dict(IPid=ip.IPid))

    def get(self):
        """商品详情"""
        args = parameter_required(('ipid', ))
        ipid = args.get('ipid')
        filter_args = [IntegralProduct.isdelete == False, IntegralProduct.IPid == ipid]
        if common_user() or is_tourist():
            filter_args.append(IntegralProduct.IPstatus == ApplyStatus.agree.value)
        ip = IntegralProduct.query.filter(*filter_args).first_("没有找到该商品")
        product = self._fill_ip(ip)
        return Success('获取成功', data=product)

    def list(self):
        """商品列表"""
        args = parameter_required()
        prtitle = args.get('prtitle')
        ipstatus = args.get('status')
        try:
            ipstatus = getattr(ApplyStatus, ipstatus).value
        except Exception as e:
            current_app.logger.error('integral list status error : {}'.format(e))
            ipstatus = None
        integral_balance = 0
        if common_user():
            ipstatus = ApplyStatus.agree.value
            user = User.query.filter_by_(USid=request.user.id).first()
            integral_balance = getattr(user, 'USintegral', 0)
        elif is_tourist():
            ipstatus = ApplyStatus.agree.value

        filter_args = [IntegralProduct.isdelete == False,
                       IntegralProduct.IPstatus == ipstatus,
                       Products.isdelete == False,
                       Products.PRstatus == ProductStatus.usual.value
                       ]
        if is_supplizer():
            filter_args.append(Products.CreaterId == request.user.id),
        if prtitle:
            filter_args.append(Products.PRtitle.ilike('%{}%'.format(prtitle)))
        ips = IntegralProduct.query.outerjoin(Products, Products.PRid == IntegralProduct.PRid
                                              ).filter_(*filter_args
                                                        ).order_by(IntegralProduct.createtime.desc()).all_with_page()
        for ip in ips:
            pr = Products.query.filter(Products.PRid == ip.PRid).first()
            pb = ProductBrand.query.filter(ProductBrand.PBid == pr.PBid).first()
            ip.fill('prtitle', pr.PRtitle)
            ip.fill('prmainpic', pr['PRmainpic'])
            ip.fill('ipstatus_zh', ApplyStatus(ip.IPstatus).zh_value)
            ip.fill('ipstatus_en', ApplyStatus(ip.IPstatus).name)
            ip.fill('pbname', pb.PBname)

        res = dict(product=ips)
        if common_user() or is_tourist():
            cfg = ConfigSettings()
            rule = cfg.get_item('integralrule', 'rule')
            integral = dict(balance=integral_balance, rule=rule)
            res['integral'] = integral
        return Success(data=res)

    def _fill_ip(self, ip):
        product = Products.query.filter(
            Products.PRid == ip.PRid, Products.isdelete == False).first()
        if not product:
            current_app.logger.info('·商品已删除 prid = {}'.format(ip.PRid))
        product.fields = ['PRid', 'PRtitle', 'PRstatus', 'PRmainpic', 'PRattribute', 'PRdesc', 'PRdescription', 'PRlinePrice']
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

        # 获取商品评价平均分（五颗星：0-10）
        averagescore = ip.IPaverageScore or 10
        if float(averagescore) > 10:
            averagescore = 10
        elif float(averagescore) < 0:
            averagescore = 0
        else:
            averagescore = round(averagescore)
        product.PRaverageScore = averagescore
        product.fill('fiveaveragescore', averagescore / 2)
        product.fill('ipaveragescore', averagescore)

        return product

    def cancel_apply(self):
        """取消申请"""
        if is_admin():
            Admin.query.filter_by_(ADid=request.user.id).first_("账号状态错误")
        # elif is_supplizer():
        #     Supplizer.query.filter_by_(SUid=request.user.id).first_("账号状态错误")
        else:
            raise AuthorityError()
        data = parameter_required(('ipid',))
        with db.auto_commit():
            ip = IntegralProduct.query.filter(IntegralProduct.IPid == data.get('ipid'),
                                              IntegralProduct.isdelete == False,
                                              IntegralProduct.IPstatus == ApplyStatus.wait_check.value
                                              ).first_("只有在审核状态下的申请可以撤销")
            if is_supplizer() and ip.SUid != request.user.id:
                raise AuthorityError("只能撤销属于自己的申请")
            ip.update({'IPstatus': ApplyStatus.cancle.value})
            db.session.add(ip)
            if is_admin():
                BASEADMIN().create_action(AdminAction.update.value, 'IntegralProduct', data.get('ipid'))
            # 返回库存
            product = Products.query.filter_by(PRid=ip.PRid, isdelete=False).first_('商品信息出错')
            ips_old = IntegralProductSku.query.filter(IntegralProductSku.IPid == ip.IPid,
                                                      IntegralProductSku.isdelete == False,
                                                      IntegralProduct.isdelete == False,
                                                      ).all()
            for sku in ips_old:
                sku_instance = ProductSku.query.filter_by(isdelete=False, PRid=product.PRid,
                                                          SKUid=sku.SKUid).first_('商品sku信息不存在')
                super(CIntegralStore, self)._update_stock(int(sku.IPSstock), product, sku_instance)

            # 同时取消正在进行的审批流
            Approval.query.filter_by(AVcontent=ip.IPid, AVstartid=request.user.id,
                                     isdelete=False, AVstatus=ApplyStatus.wait_check.value
                                     ).update({'AVstatus': ApplyStatus.cancle.value})
        return Success('已取消申请', dict(ipid=ip.IPid))

    def delete(self):
        """删除申请"""
        # if is_supplizer():
        #     usid = request.user.id
        #     sup = Supplizer.query.filter_by_(SUid=usid).first_('供应商信息错误')
        #     suid = sup.SUid
        #     current_app.logger.info('Supplizer {} delete integral apply'.format(sup.SUname))
        if is_admin():
            usid = request.user.id
            admin = Admin.query.filter_by_(ADid=usid).first_('管理员信息错误')
            current_app.logger.info('Admin {} delete integral apply'.format(admin.ADname))
            sup = None
            suid = None
        else:
            raise AuthorityError()
        data = parameter_required(('ipid',))
        ipid = data.get('ipid')
        with db.auto_commit():
            apply_info = IntegralProduct.query.filter_by(IPid=ipid, isdelete=False).first_('没有该商品记录')
            if sup and apply_info.SUid != suid:
                raise ParamsError('只能删除自己提交的申请')
            if apply_info.IPstatus not in [ApplyStatus.cancle.value, ApplyStatus.reject.value,
                                           ApplyStatus.shelves.value]:
                raise StatusError('只能删除已下架或已撤销状态下的申请')
            apply_info.isdelete = True
            IntegralProductSku.query.filter(IntegralProductSku.IPid == apply_info.IPid).delete_()
            if is_admin():
                BASEADMIN().create_action(AdminAction.delete.value, 'IntegralProduct', apply_info.IPid)
        return Success('删除成功', {'ipid': ipid})

    def shelf(self):
        """下架"""
        # if is_supplizer():
        #     usid = request.user.id
        #     sup = Supplizer.query.filter_by_(SUid=usid).first_('供应商信息错误')
        #     current_app.logger.info('Supplizer {} shelf integral apply'.format(sup.SUname))
        if is_admin():
            usid = request.user.id
            admin = Admin.query.filter_by_(ADid=usid).first_('管理员信息错误')
            current_app.logger.info('Admin {} shelf integral apply'.format(admin.ADname))
            sup = None
        else:
            raise AuthorityError()
        data = parameter_required(('ipid',))
        ipid = data.get('ipid')
        with db.auto_commit():
            ip = IntegralProduct.query.filter_by_(IPid=ipid).first_('无此申请记录')
            if sup and ip.SUid != usid:
                raise StatusError('只能下架自己的商品')
            if ip.IPstatus != ApplyStatus.agree.value:
                raise StatusError('只能下架已上架的商品')
            ip.IPstatus = ApplyStatus.shelves.value
            if is_admin():
                BASEADMIN().create_action(AdminAction.update.value, 'IntegralProduct', ipid)
            # 返回库存
            product = Products.query.filter_by(PRid=ip.PRid, isdelete=False).first_('商品信息出错')
            ips_old = IntegralProductSku.query.filter(IntegralProductSku.IPid == ip.IPid,
                                                      IntegralProductSku.isdelete == False,
                                                      IntegralProduct.isdelete == False,
                                                      ).all()
            for sku in ips_old:
                sku_instance = ProductSku.query.filter_by(isdelete=False, PRid=product.PRid,
                                                          SKUid=sku.SKUid).first_('商品sku信息不存在')
                super(CIntegralStore, self)._update_stock(int(sku.IPSstock), product, sku_instance)
        return Success('下架成功', {'ipid': ipid})

    @token_required
    def order(self):
        """下单"""
        data = parameter_required(('ipid', 'pbid', 'ipsid', 'omclient', 'uaid'))
        usid = request.user.id
        user = User.query.filter_by_(USid=usid).first_("请重新登录")
        current_app.logger.info('User {} is buying a Integral Product'.format(user.USname))
        uaid = data.get('uaid')
        ipid = data.get('ipid')
        opaytype = data.get('opaytype', 30)  # 支付方式
        try:
            omclient = int(data.get('omclient', Client.wechat.value))  # 下单设备
            Client(omclient)
        except Exception:
            raise ParamsError('客户端来源错误')
        with db.auto_commit():
            # 用户的地址信息
            user_address_instance = db.session.query(UserAddress).filter_by_({'UAid': uaid, 'USid': usid}).first_(
                '地址信息不存在')
            omrecvphone = user_address_instance.UAphone
            areaid = user_address_instance.AAid
            # 地址拼接
            area, city, province = db.session.query(AddressArea, AddressCity, AddressProvince).filter(
                AddressArea.ACid == AddressCity.ACid, AddressCity.APid == AddressProvince.APid).filter(
                AddressArea.AAid == areaid).first_('地址有误')
            address = getattr(province, "APname", '') + getattr(city, "ACname", '') + getattr(area, "AAname", '')
            omrecvaddress = address + user_address_instance.UAtext
            omrecvname = user_address_instance.UAname
            opayno = self.wx_pay.nonce_str
            model_bean = []

            omid = str(uuid.uuid1())
            pbid = data.get('pbid')
            ommessage = data.get('ommessage')
            product_brand_instance = db.session.query(ProductBrand).filter_by_({'PBid': pbid}).first_(
                '品牌id: {}不存在'.format(pbid))

            opid = str(uuid.uuid1())
            skuid = data.get('ipsid')
            opnum = int(data.get('nums', 1))
            # opnum = 1  # 购买数量暂时只支持一件
            # assert opnum > 0, 'nums <= 0, 参数错误'
            sku_instance = IntegralProductSku.query.filter_by_(IPSid=skuid).first_(
                'ipsid: {}不存在'.format(skuid))
            product_sku = ProductSku.query.filter_by_(SKUid=sku_instance.SKUid).first_("商品sku不存在")
            if sku_instance.IPid != ipid:
                raise ParamsError('skuid 与 ipid 商品不对应')
            if int(sku_instance.IPSstock) - int(opnum) < 0:
                raise StatusError('商品库存不足')
            integral_product = IntegralProduct.query.filter(IntegralProduct.IPid == ipid,
                                                            IntegralProduct.isdelete == False,
                                                            IntegralProduct.IPstatus == ApplyStatus.agree.value,
                                                            ).first_("ipid: {}对应的星币商品不存在")
            product_instance = Products.query.filter(Products.isdelete == False,
                                                     Products.PRid == integral_product.PRid,
                                                     Products.PRstatus == ProductStatus.usual.value
                                                     ).first_('ipid: {}对应的商品不存在'.format(skuid))
            if product_instance.PBid != pbid:
                raise ParamsError('品牌id: {}与skuid: {}不对应'.format(pbid, skuid))
            small_total = int(sku_instance.SKUprice) * opnum
            order_part_dict = {
                'OMid': omid,
                'OPid': opid,
                'PRid': integral_product.IPid,  # 是星币商品id，不是原商品
                'SKUid': skuid,
                'PRattribute': product_instance.PRattribute,
                'SKUattriteDetail': product_sku.SKUattriteDetail,
                'PRtitle': product_instance.PRtitle,
                'SKUprice': sku_instance.SKUprice,
                'PRmainpic': product_instance.PRmainpic,
                'OPnum': opnum,
                'OPsubTotal': small_total,
                'PRfrom': product_instance.PRfrom,
            }
            order_part_instance = OrderPart.create(order_part_dict)
            model_bean.append(order_part_instance)

            # 对应商品销量 + num sku库存 -num
            db.session.query(IntegralProduct).filter_by_(IPid=ipid).update({
                'IPsaleVolume': IntegralProduct.IPsaleVolume + opnum})
            db.session.query(IntegralProductSku).filter_by_(IPSid=skuid).update({
                'IPSstock': IntegralProductSku.IPSstock - opnum})

            # 主单
            order_main_dict = {
                'OMid': omid,
                'OMno': self._generic_omno(),
                'OPayno': opayno,
                'USid': usid,
                'OMfrom': OrderFrom.integral_store.value,
                'PBname': product_brand_instance.PBname,
                'PBid': product_brand_instance.PBid,
                'OMclient': omclient,
                'OMfreight': 0,  # 运费暂时为0
                'OMmount': small_total,
                'OMmessage': ommessage,
                'OMtrueMount': small_total,
                # 收货信息
                'OMrecvPhone': omrecvphone,
                'OMrecvName': omrecvname,
                'OMrecvAddress': omrecvaddress,
                'PRcreateId': product_instance.CreaterId,
                'UseCoupon': False
            }
            order_main_instance = OrderMain.create(order_main_dict)
            model_bean.append(order_main_instance)

            # 支付数据表
            order_pay_dict = {
                'OPayid': str(uuid.uuid1()),
                'OPayno': opayno,
                'OPayType': PayType.integralpay.value,  # 星币支付
                'OPayMount': small_total,
            }
            order_pay_instance = OrderPay.create(order_pay_dict)
            model_bean.append(order_pay_instance)
            db.session.add_all(model_bean)
        from planet.extensions.tasks import auto_cancle_order
        auto_cancle_order.apply_async(args=([omid],), countdown=30 * 60, expires=40 * 60, )
        # # 生成支付信息
        # body = product_instance.TCtitle
        # pay_args = self._pay_detail(omclient, opaytype, opayno, float(small_total), body,
        #                             openid=user.USopenid1 or user.USopenid2)
        response = {
            'pay_type': PayType(opaytype).name,
            'opaytype': opaytype,
            'usintegral': getattr(user, 'USintegral', 0),
            'omid': omid,
            'omtruemount': small_total
            # 'args': pay_args
        }
        return Success('创建成功', data=response)

    def _check_price(self, price):
        if not str(price).isdigit() or int(price) <= 0:
            raise ParamsError("数字'{}'错误， 只能输入大于0的整数".format(price))
        return price





