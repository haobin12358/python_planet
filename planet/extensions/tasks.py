# -*- coding: utf-8 -*-
import uuid
from datetime import date, timedelta, datetime

from flask import current_app
from flask_celery import Celery
from sqlalchemy import cast, Date

from planet import create_app
from planet.common.share_stock import ShareStock
from planet.config.enums import OrderMainStatus, OrderFrom
from planet.extensions.register_ext import db
from planet.models import CorrectNum, GuessNum, GuessAwardFlow, ProductItems, OrderMain, OrderPart, OrderEvaluation, \
    Products

celery = Celery()


@celery.task(name="fetch_share_deal")
def fetch_share_deal():
    """获取昨日的收盘"""
    with db.auto_commit():
        s_list = []
        share_stock = ShareStock()
        yesterday_result = share_stock.new_result()
        yesterday = date.today() - timedelta(days=1)
        # 昨日结果
        db_yesterday = CorrectNum.query.filter(
            cast(CorrectNum.CNdate, Date) == yesterday
        ).first()
        if not db_yesterday:  # 昨日
            current_app.logger.info('写入昨日数据')
            correct_instance = CorrectNum.create({
                'CNid': str(uuid.uuid4()),
                'CNnum': yesterday_result,
                'CNdate': yesterday
            })
            s_list.append(correct_instance)
            # 判断是否有猜对的
            guess_nums = GuessNum.query.filter_by({'GNnum': yesterday_result, 'GNdate': db_yesterday}).all()
            for guess_num in guess_nums:
                exists_in_flow = GuessAwardFlow.query.filter_by_({'GNid': guess_num.GNid}).first()
                if not exists_in_flow:
                    guess_award_flow_instance = GuessAwardFlow.create({
                        'GAFid': str(uuid.uuid4()),
                        'GNid': guess_num.GNid,
                    })
                    s_list.append(guess_award_flow_instance)
        if s_list:
            db.session.add_all(s_list)


@celery.task(name='auto_evaluate')
def auto_evaluate():
    """超时自动评价订单"""
    with db.auto_commit():
        s_list = list()
        order_mains = OrderMain.query.filter(OrderMain.OMstatus == OrderMainStatus.wait_comment.value,
                                             OrderMain.OMfrom.in_([OrderFrom.carts.value, OrderFrom.product_info.value]),
                                             OrderMain.createtime + timedelta(days=30) >= datetime.now()
                                             ).all()  # 所有超过30天待评价的商品订单
        for order_main in order_mains:
            order_parts = OrderPart.query.filter_by_(OMid=order_main.OMid).all()  # 主单下所有副单
            for order_part in order_parts:
                evaluation_dict = {
                    'OEid': str(uuid.uuid1()),
                    'USid': order_main.USid,
                    'OPid': order_part.OPid,
                    'OMid': order_main.OMid,
                    'PRid': order_part.PRid,
                    'SKUattriteDetail': order_part.SKUattriteDetail,
                    'OEtext': '此用户没有填写评价。',
                    'OEscore': 5,
                }
                evaluation_instance = OrderEvaluation.create(evaluation_dict)
                s_list.append(evaluation_instance)
                # 商品总体评分变化
                try:
                    product_info = Products.query.filter_by_(PRid=order_part.PRid).first()
                    average_score = round((float(product_info.PRaverageScore) + 10) / 2)
                    Products.query.filter_by_(PRid=order_part.PRid).update({'PRaverageScore': average_score})
                except Exception as e:
                    current_app.logger.info("Auto Evaluation , Update Product Score ERROR, is {}".format(e))
            # 更改主单待评价状态为已完成
            OrderMain.query.filter_by_(OMid=order_main.OMid).update({'OMstatus': OrderMainStatus.ready.value})
        if s_list:
            db.session.add_all(s_list)


if __name__ == '__main__':
    app = create_app()
    with app.app_context():
        fetch_share_deal()

 # # 今日结果
        # db_today = CorrectNum.query.filter(
        #     cast(CorrectNum.CNdate, Date) == date.today()
        # ).first()
        # if hasattr(share_stock, 'today_result') and not db_today:  # 今日
        #     current_app.logger.info('写入今日数据')
        #     correct_instance = CorrectNum.create({
        #         'CNid': str(uuid.uuid4()),
        #         'CNnum': share_stock.today_result,
        #         'CNdate': date.today()
        #     })
        #     s_list.append(correct_instance)
        #
        #     # 判断是否有猜对的
        #     guess_nums = GuessNum.query.filter_by({'GNnum': share_stock.today_result, 'GNdate': date.today()}).all()
        #     for guess_num in guess_nums:
        #         exists_in_flow = GuessAwardFlow.query.filter_by_({'GNid': guess_num.GNid}).first()
        #         if not exists_in_flow:
        #             guess_award_flow_instance = GuessAwardFlow.create({
        #                 'GAFid': str(uuid.uuid4()),
        #                 'GNid': guess_num.GNid,
        #             })
        #             s_list.append(guess_award_flow_instance)
        #
        # db_today = CorrectNum.query.filter(
        #     cast(CorrectNum.CNdate, Date) == date.today()
        # ).first()
