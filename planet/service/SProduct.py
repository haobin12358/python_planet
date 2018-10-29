# -*- coding: utf-8 -*-
from planet.common.base_service import SBase, close_session
from planet.models.model import Products


class SProducts(SBase):
    @close_session
    def get_product_by_prid(self, prid):
        return self.session.query(Products).filter_by_(
            PRid=prid
        ).first()

