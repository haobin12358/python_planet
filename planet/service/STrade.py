# -*- coding: utf-8 -*-
from planet.common.base_service import SBase, close_session
from planet.models.trade import Carts


class STrade(SBase):
    @close_session
    def get_card_list(self, args):
        """获取购物车列表"""
        pbids = self.session.query(Carts.PBid).filter_by_(**args).group_by(Carts.PBid).all_with_page()
        return self.session.query(Carts).filter(Carts.PBid.in_([x.PBid for x in pbids])).\
            filter_by_(**args).order_by(Carts.createtime).\
            all()

    @close_session
    def get_card_one(self, args, error=None):
        return self.session.query(Carts).filter_by_(**args).first_(error)

