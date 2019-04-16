import uuid
from flask import current_app
from planet.common.params_validates import parameter_required
from planet.common.success_response import Success
from planet.config.enums import OrderMainStatus, LogisticsSignStatus
from planet.extensions.register_ext import db
from planet.control.COrder import COrder
from planet.models import OrderMain, OrderLogistics, OrderPart, User, OrderEvaluation, Products


class Test(object):

    def auto_complete_order(self):
        data = parameter_required(('omno',))
        omno = data.get('omno')
        with db.auto_commit():
            corder = COrder()
            order_main = OrderMain.query.filter(OrderMain.OMno == omno,
                                                OrderMain.isdelete == False,
                                                OrderMain.OMstatus == OrderMainStatus.wait_recv.value,
                                                ).first_("该订单不存在或不是待收货状态")
            current_app.logger.info("订单OMid: {} 开始运行自动完成任务".format(order_main.OMid))
            order_parts = OrderPart.query.filter_by_(OMid=order_main.OMid).all()  # 主单下所有副单
            current_app.logger.info("该订单下有 {} 个副单".format(len(order_parts)))
            for order_part in order_parts:
                current_app.logger.info("副单OPid {} ".format(order_part.OPid))
                user = User.query.filter_by(USid=order_main.USid, isdelete=False).first_("订单用户不存在")
                try:
                    current_app.logger.info("开始进行佣金到账")
                    corder._fresh_commsion_into_count(order_part)  # 佣金到账
                except Exception as e:
                    current_app.logger.error("佣金到账出错: {}".format(e))
                current_app.logger.info("佣金到账结束")
                try:
                    current_app.logger.info("开始进行销售量统计")
                    corder._tosalesvolume(order_main.OMtrueMount, user.USid)  # 销售额统计
                except Exception as e:
                    current_app.logger.error("销售量统计出错: {}".format(e))

                usname, usheader = user.USname, user.USheader

                # 创建评价
                evaluation_dict = {
                    'OEid': str(uuid.uuid1()),
                    'USid': order_main.USid,
                    'USname': usname,
                    'USheader': usheader,
                    'OPid': order_part.OPid,
                    'OMid': order_main.OMid,
                    'PRid': order_part.PRid,
                    'SKUattriteDetail': order_part.SKUattriteDetail,
                    'OEtext': '此用户没有填写评价。',
                    'OEscore': 5,
                }
                db.session.add(OrderEvaluation.create(evaluation_dict))

                # 更改商品评分
                try:
                    product_info = Products.query.filter_by_(PRid=order_part.PRid).first_("商品不存在")
                    scores = [oe.OEscore for oe in
                              OrderEvaluation.query.filter(OrderEvaluation.PRid == product_info.PRid,
                                                           OrderEvaluation.isdelete == False).all()]
                    average_score = round(((float(sum(scores)) + float(5.0)) / (len(scores) + 1)) * 2)
                    Products.query.filter_by(PRid=order_part.PRid).update({'PRaverageScore': average_score})
                except Exception as e:
                    current_app.logger.info("更改商品评分失败, 商品可能已被删除；Update Product Score ERROR ：{}".format(e))

            # 物流同步更改状态
            ol = OrderLogistics.query.filter(OrderLogistics.OMid == order_part.OMid,
                                             OrderLogistics.isdelete == False,
                                             OrderLogistics.OLsignStatus != LogisticsSignStatus.already_signed.value
                                             ).update({'OLsignStatus': LogisticsSignStatus.already_signed.value},
                                                      synchronize_session=False)
            if ol:
                current_app.logger.info("订单 OMid: {} 存在物流，提前确认收货".format(order_main.OMid))
            # 更改主单状态
            order_main.update({'OMstatus': OrderMainStatus.ready.value})
            db.session.add(order_main)
        current_app.logger.info("订单自动完成任务结束")
        return Success('更改成功', dict(OMid=order_main.OMid))


# if __name__ == '__main__':
    # app = create_app()
    # with app.app_context():
        # Test().auto_complete_order()
