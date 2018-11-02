# -*- coding: utf-8 -*-
import uuid
from decimal import Decimal

from planet import ParamsError
from planet.common.params_validates import parameter_required
from planet.common.success_response import Success
from planet.common.token_handler import token_required
from planet.config.enums import ORDER_FROM, ORDER_CLIENT
from planet.models import ProductSku, Product
from planet.models.trade import OrderMain, OrderPart, OrderPay
from planet.service.STrade import STrade


class COrder:
    def __init__(self):
        self.strade = STrade()

    @token_required
    def create(self):
        data = parameter_required(('info', 'omclient', 'omfrom', 'udid', 'opaytype'))
        # todo udid 表示用户的地址信息
        usid = request.user.id
        udid = data.get('udid')
        opaytype = data.get('opaytype')

        try:
            omclient = int(data.get('omclient', 0))  # 下单设备
            omfrom = int(data.get('omfrom', 0))  # 商品来源
            assert omclient in ORDER_FROM
            assert omfrom in ORDER_CLIENT
        except Exception as e:
            raise ParamsError('客户端或商品来源错误')
        infos = data.get('info')
        with self.strade.auto_commit() as s:
            opayid = str(uuid.uuid4())
            model_bean = []
            mount_price = Decimal()  # 此次支付的总价
            for info in infos:
                order_price = Decimal()  # 价格
                omid = str(uuid.uuid4())  # 主单id
                info = parameter_required(('pbid', 'skus', ))
                pbid = info.get('pbid')
                skus = info.get('skus')
                ommessage = info.get('ommessage')
                for sku in skus:
                    # 订单副单
                    opid = str(uuid.uuid4())
                    skuid = sku.get('skuid')
                    opnum = int(sku.get('opnum', 1))
                    assert opnum > 0
                    sku_instance = s.query(ProductSku).filter_by_({'SKUid': skuid}).first_('skuid{}不存在'.format(skuid))
                    prid = sku_instance.PRid
                    product_instance = s.query(Product).filter_by_({'PRid': prid}).first_('skuid{}对应的商品不存在'.format(skuid))
                    if product_instance.PBid != pbid:
                        raise ParamsError('品牌id不对应')
                    product_brand_instance = s.query(ProductBrand).filter_by_by({'PBid': pbid})
                    small_total = Decimal(str(sku_instance.SKUprice)) * opnum

                    order_part_dict = {
                        'OMid': omid,
                        'OPid': opid,
                        'SKUid': skuid,
                        'SKUdetail': sku_instance.SKUdetail,
                        'PRtitle': product_instance.PRtitle,
                        'PRmainpic': product_instance.PRmainpic,
                        'OPnum': opnum,
                        'OPsubTotal': float(small_total),
                    }
                    order_part_instance = OrderPart.create(order_part_dict)
                    model_bean.append(order_part_instance)
                    # 价格累加
                    order_price += small_total
                # 主单
                order_main_dict = {
                    'OMid': omid,
                    'OMno': self._generic_omno(),
                    'OPayid': opayid,
                    'USid': usid,
                    'OMfrom': omfrom,
                    'PBname': product_brand_instance.PBname,
                    'PBid': pbid,
                    'OMclient': omclient,
                    'OMfreight': 0, # 运费暂时为0
                    'OMmount':small_totals,
                    'OMmessage': ommessage,
                    'OMtrueMount': order_price,  # 暂时付费不优惠
                    # 收货信息
                    'OMrecvPhone': omrecvphone,
                    'OMrecvName': omrecvname,
                    'OMrecvAddress': omrecvaddress,
                }
                order_main_instance = OrderMain.create(order_main_dict)
                model_bean.append(order_main_instance)
                mount_price += order_price
            # 支付数据
            order_pay_dict = {
                'OPayid': opayid,
                'OPaysn': '',
                'OPayType': opaytype,
                'OPayMount': mount_price
            }
            order_pay_instance = OrderPay.create(order_pay_dict)
            model_bean.append(order_pay_instance)
            s.add_all(model_bean)
        return Success()


    @staticmethod
    def _generic_omno():
        """生成订单号"""
         return str(time.strftime('%Y%m%d%H%M%S', time.localtime(time.time()))) \
                     + str(time.time()).replace('.', '')[-7:]
