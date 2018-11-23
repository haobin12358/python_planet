# -*- coding: utf-8 -*-
import uuid
from datetime import datetime, date, timedelta

from flask import request
from sqlalchemy import cast, Date, extract

from planet.common.error_response import StatusError, ParamsError
from planet.common.success_response import Success
from planet.common.token_handler import token_required
from planet.extensions.register_ext import db
from planet.extensions.validates.activty import GuessNumCreateForm, GuessNumGetForm, GuessNumHistoryForm
from planet.models.activity import GuessNum, CorrectNum


class CGuessNum:
    @token_required
    def creat(self):
        """参与活动"""
        date_now = datetime.now()
        if date_now.hour > 15:
            raise StatusError('15点以后不开放')
        form = GuessNumCreateForm().valid_data()
        gnnum = form.gnnum.data
        usid = request.user.id

        # if date_now.hour > 15:  # 15点以后参与次日的
        #     gndate = date.today() + timedelta(days=1)
        # else:
        #     gndate = date.today()

        with db.auto_commit():
            guess_instance = GuessNum.create({
                'GNid': str(uuid.uuid4()),
                'GNnum': gnnum,
                'USid': usid,
                # 'GNdate': gndate
            })
            db.session.add(guess_instance)
        return Success('参与成功')

    @token_required
    def get(self):
        """获得单日个人参与"""
        form = GuessNumGetForm().valid_data()
        usid = request.user.id
        guess_num_instance = GuessNum.query.filter_(
            GuessNum.USid == usid,
            cast(GuessNum.createtime, Date) == form.date.data,
            GuessNum.isdelete == False
        ).first()
        if guess_num_instance:
            guess_num_instance.hide('USid').add('createtime')
        else:
            guess_num_instance = {}
        return Success(data=guess_num_instance)

    @token_required
    def history_join(self):
        """获取历史参与记录"""
        form = GuessNumHistoryForm().valid_data()
        year = form.year.data
        month = form.month.data
        try:
            year_month = datetime.strptime(year + '-' + month,  '%Y-%m')
        except ValueError as e:
            raise ParamsError('时间参数异常')
        usid = request.user.id
        join_historys = GuessNum.query.filter(
            extract('month', GuessNum.GNdate) == year_month.month,
            extract('year', GuessNum.GNdate) == year_month.year,
            GuessNum.USid == usid
        ).order_by(GuessNum.GNdate.desc()).group_by(GuessNum.GNdate).all()
        for join_history in join_historys:
            correct_num = CorrectNum.query.filter(
                join_history.GNdate == CorrectNum.CNdate
            ).first()
            join_history.fill('correct_num', correct_num)
            if not correct_num:
                result = 'not_open'
            else:
                correct_num.hide('CNid')
                if correct_num.CNnum == GuessNum.GNnum:
                    result = 'correct'
                else:
                    result = 'uncorrect'
            join_history.fill('result', result).hide('USid', )
        return Success(data=join_historys)








