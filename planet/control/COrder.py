# -*- coding: utf-8 -*-
import uuid

from planet import ParamsError
from planet.common.params_validates import parameter_required
from planet.config.enums import ORDER_FROM, ORDER_CLIENT
from planet.models import ProductSku
from planet.models.trade import OrderMain
from planet.service.STrade import STrade


class COrder:
    def __init__(self):
        self.strade = STrade()

    def create(self):
        data = parameter_required(('omclient', 'omfrom'))
        try:
            omclient = int(data.get('omclient', 0))  # 下单设备
            omfrom = int(data.get('omfrom', 0))  # 商品来源
            assert omclient in ORDER_FROM
            assert omfrom in ORDER_CLIENT
        except Exception as e:
            raise ParamsError('客户端或商品来源错误')
        with self.strade.auto_commit() as s:
            # 一个品牌一个订单
            pass
            # omid = str(uuid.uuid4())
            # sku = s.query(ProductSku).filter_by_({'SKUid': skuid}).first_('sku不存在')
            # order_part_dict = {
            #     ''
            # }



