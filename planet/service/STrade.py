# -*- coding: utf-8 -*-
from planet.common.base_service import SBase, close_session
from planet.models.trade import Carts, OrderMain, OrderPart, LogisticsCompnay, OrderRefundApply, OrderLogistics
from planet.models.trade import OrderEvaluation, OrderEvaluationImage, OrderEvaluationVideo


class STrade(SBase):
    @close_session
    def get_card_list(self, args):
        """获取购物车列表"""
        brands = self.session.query(Carts).filter_by_(**args)
        pbids = brands.group_by(Carts.PBid).order_by(Carts.createtime.desc()).all_with_page()
        return brands.filter(Carts.PBid.in_([x.PBid for x in pbids])).\
            order_by(Carts.createtime.desc()).all()

    @close_session
    def get_card_one(self, args, error=None):
        return self.session.query(Carts).filter_by_(**args).first_(error)

    @close_session
    def get_ordermain_list(self, args):
        return self.session.query(OrderMain).filter_(*args, OrderMain.isdelete == False
                                                     ).order_by(OrderMain.createtime.desc()).all_with_page()

    @close_session
    def get_ordermain_one(self, args, error=None):
        return self.session.query(OrderMain).filter_by_(
            args
        ).first_(error)

    @close_session
    def update_ordermain_one(self, args, upinfo):
        return self.session.query(OrderMain).filter(*args).update(upinfo)

    @close_session
    def get_orderpart_list(self, args):
        return self.session.query(OrderPart).filter_by_(
            **args
        ).all()

    @close_session
    def get_logisticscompany_list(self, args):
        return self.session.query(LogisticsCompnay).filter_by_().filter_(*args).all_with_page()

    @close_session
    def get_orderrefundapply_one(self, args, error=None):
        """获取单个售后申请"""
        return self.session.query(OrderRefundApply).filter_by_(args).order_by(OrderRefundApply.createtime.desc()).first_(error)


    @close_session
    def get_orderlogistics_one(self, args, error=None):
        """获取单个物流信息"""
        return self.session.query(OrderLogistics).filter_by_(args).first_(error)

    @close_session
    def get_order_evaluation(self, args):
        """获取订单评价"""
        return self.session.query(OrderEvaluation).filter_by_(**args).order_by(OrderEvaluation.createtime.desc()
                                                                               ).all_with_page()

    @close_session
    def del_order_evaluation(self, oeid):
        """删除订单评价"""
        return self.session.query(OrderEvaluation).filter_by(OEid=oeid).delete_()

    @close_session
    def get_order_evaluation_image(self, oeid):
        """获取订单评价图片"""
        return self.session.query(OrderEvaluationImage).filter_by_(OEid=oeid).all()

    @close_session
    def del_order_evaluation_image(self, oeid):
        """删除订单评价图片"""
        return self.session.query(OrderEvaluationImage).filter_by(OEid=oeid).delete_()

    @close_session
    def get_order_evaluation_video(self, oeid):
        """获取订单评价视频"""
        return self.session.query(OrderEvaluationVideo).filter_by_(OEid=oeid).all()

    @close_session
    def del_order_evaluation_video(self, oeid):
        """删除订单评价视频"""
        return self.session.query(OrderEvaluationVideo).filter_by(OEid=oeid).delete_()
