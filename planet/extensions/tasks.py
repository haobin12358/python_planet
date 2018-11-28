# -*- coding: utf-8 -*-
import uuid
from datetime import date, timedelta

from flask import current_app
from flask_celery import Celery
from sqlalchemy import cast, Date

from planet import create_app
from planet.common.share_stock import ShareStock
from planet.extensions.register_ext import db
from planet.models import CorrectNum, GuessNum, GuessAwardFlow, ProductItems

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
