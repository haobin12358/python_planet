# -*- coding: utf-8 -*-
from planet.common.base_service import SBase, close_session
from planet.models.trade import Carts


class STrade(SBase):
    @close_session
    def get_card_list(self, args):
        return self.session.query(Carts).filter_by_(**args).group(Carts.PBid).all()

    @close_session
    def get_card_one(self, args):
        return self.session.query(Carts).filter_by_(**args).first()
