# -*- coding: utf-8 -*-
import uuid
from datetime import date, timedelta, datetime

from flask import current_app
from flask_celery import Celery
from sqlalchemy import cast, Date, extract, func

from planet.common.error_response import NotFound
from planet.common.share_stock import ShareStock
from planet.config.cfgsetting import ConfigSettings
from planet.config.enums import OrderMainStatus, OrderFrom, UserCommissionStatus, ProductStatus, ApplyStatus, ApplyFrom, \
    SupplizerSettementStatus, LogisticsSignStatus
from planet.extensions.register_ext import db
from planet.models import CorrectNum, GuessNum, GuessAwardFlow, ProductItems, OrderMain, OrderPart, OrderEvaluation, \
    Products, User, UserCommission, Approval, Supplizer, SupplizerSettlement

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
    cfs = ConfigSettings()
    limit_time = cfs.get_item('order_auto', 'auto_evaluate_day')
    with db.auto_commit():
        s_list = list()
        current_app.logger.info(">>>>>>  开始检测超过{0}天未评价的商品订单  <<<<<<".format(limit_time))
        from planet.control.COrder import COrder
        corder = COrder()
        count = 0
        order_mains = OrderMain.query.filter(OrderMain.OMstatus == OrderMainStatus.wait_comment.value,
                                             OrderMain.OMfrom.in_(
                                                 [OrderFrom.carts.value, OrderFrom.product_info.value]),
                                             OrderMain.createtime <= datetime.now() - timedelta(days=int(limit_time))
                                             ).all()  # 所有超过30天待评价的商品订单
        if not order_mains:
            current_app.logger.info(">>>>>>  没有超过{0}天未评价的商品订单  <<<<<<".format(limit_time))
        else:
            for order_main in order_mains:
                order_parts = OrderPart.query.filter_by_(OMid=order_main.OMid).all()  # 主单下所有副单
                for order_part in order_parts:
                    if order_part.OPisinORA is True:
                        continue
                    exist_evaluation = OrderEvaluation.query.filter_by_(OPid=order_part.OPid).first()
                    if exist_evaluation:
                        current_app.logger.info(
                            ">>>>> ERROR, 该副单已存在评价, OPid : {}, OMid : {}".format(order_part.OPid, order_part.OMid))
                        continue
                    user = User.query.filter_by(USid=order_main.USid).first()
                    if order_part.OPisinORA:
                        continue

                    # user_commision = UserCommission.query.filter(
                    #     UserCommission.isdelete == False,
                    #     UserCommission.OPid == order_part.OPid
                    # ).update({
                    #     'UCstatus': UserCommissionStatus.in_account.value
                    # })
                    corder._commsion_into_count(order_part)  # 佣金到账
                    corder._tosalesvolume(order_main.OMtrueMount, user.USid)  # 销售额统计
                    # current_app.logger.info('佣金到账数量 {}'.format(user_commision))
                    if user:
                        usname, usheader = user.USname, user.USheader
                    else:
                        usname, usheader = '神秘的客官', ''
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
                    evaluation_instance = OrderEvaluation.create(evaluation_dict)
                    s_list.append(evaluation_instance)
                    count += 1
                    current_app.logger.info(
                        ">>>>>>  评价第{0}条，OPid ：{1}  <<<<<<".format(str(count), str(order_part.OPid)))
                    # 佣金到账
                    # 商品总体评分变化
                    try:
                        product_info = Products.query.filter_by_(PRid=order_part.PRid).first()
                        average_score = round((float(product_info.PRaverageScore) + 10) / 2)
                        Products.query.filter_by_(PRid=order_part.PRid).update({'PRaverageScore': average_score})
                    except Exception as e:
                        current_app.logger.info("更改商品评分失败, 商品可能已被删除；Update Product Score ERROR ：{}".format(e))

                # 更改主单待评价状态为已完成
                change_status = OrderMain.query.filter_by_(OMid=order_main.OMid).update(
                    {'OMstatus': OrderMainStatus.ready.value})
                if change_status:
                    current_app.logger.info(">>>>>>  主单状态更改成功 OMid : {}  <<<<<<".format(str(order_main.OMid)))
                else:
                    current_app.logger.info(">>>>>>  主单状态更改失败 OMid : {}  <<<<<<".format(str(order_main.OMid)))
        if s_list:
            db.session.add_all(s_list)
        current_app.logger.info(">>>>>> 自动评价任务结束，共更改{}条数据  <<<<<<".format(count))


@celery.task(name='fix_evaluate_status_error')
def fix_evaluate_status_error():
    """修改评价异常数据（已评价，未修改状态）"""
    current_app.logger.info("----->  开始检测商品评价异常数据  <-----")
    with db.auto_commit():
        order_evaluations = OrderEvaluation.query.filter_by_().all()
        count = 0
        for oe in order_evaluations:
            om = OrderMain.query.filter(OrderMain.OMid == oe.OMid, OrderMain.OMfrom.in_([OrderFrom.carts.value,
                                                                                         OrderFrom.product_info.value]
                                                                                        )).first()
            if not om:
                om_info = OrderMain.query.filter(OrderMain.OMid == oe.OMid).first()
                current_app.logger.info("-->  存在有评价，主单已删除或来自活动订单，OMid为{0}, OMfrom为{1}  <--".format(str(oe.OMid), str(om_info.OMfrom)))
                continue
            omid = om.OMid
            omstatus = om.OMstatus
            if int(omstatus) == OrderMainStatus.wait_comment.value:
                current_app.logger.info("-->  已存在评价的主单id为 {}，未修改前的主单状态为{}  <--".format(str(omid), str(omstatus)))
                current_app.logger.info("-->  开始更改状态  <--")
                upinfo = OrderMain.query.filter_by_(OMid=omid).update({'OMstatus': OrderMainStatus.ready.value})
                count += 1
                if upinfo:
                    current_app.logger.info("-->  {}:更改状态成功  <--".format(str(omid)))
                else:
                    current_app.logger.info("-->  {}:更改失败  <--".format(str(omid)))
                current_app.logger.info("--------------分割线----------------------")
                current_app.logger.info("--------------分割线----------------------")
            else:
                current_app.logger.info("----->  没有发现商品评价异常数据  <-----")
        current_app.logger.info("----->  更新结束，共更改{}条数据  <-----".format(str(count)))


@celery.task(name='create_settlenment')
def create_settlenment():
    """每月22号创建结算单"""
    current_app.logger.info("----->  开始创建供应商结算单  <-----")
    with db.auto_commit():
        su_list = Supplizer.query.filter(Supplizer.isdelete == False).all()
        for su in su_list:
            today = datetime.now()
            pre_month = date(year=today.year, month=today.month, day=1) - timedelta(days=1)
            tomonth_22 = date(year=today.year, month=today.month, day=22)
            pre_month_22 = date(year=pre_month.year, month=pre_month.month, day=22)
            su_comiission = db.session.query(func.sum(UserCommission.UCcommission)).filter(
                UserCommission.USid == su.SUid,
                UserCommission.isdelete == False,
                UserCommission.UCstatus == UserCommissionStatus.in_account.value,
                UserCommission.CommisionFor == ApplyFrom.supplizer.value,
                UserCommission.createtime < tomonth_22,
                UserCommission.createtime >= pre_month_22,
            ).first()
            ss_total = su_comiission[0]
            ss = SupplizerSettlement.create({
                'SSid': str(uuid.uuid1()),
                'SUid': su.SUid,
                'SSdealamount': float('%.2f' % float(ss_total)),
                'SSstatus': SupplizerSettementStatus.settlementing.value
            })
            db.session.add(ss)


@celery.task(name='get_logistics')
def get_logistics():
    """获取快递信息, 每天一次"""
    from planet.models import OrderLogistics
    from planet.control.CLogistic import CLogistic
    clogistic = CLogistic()
    time_now = datetime.now()
    order_logisticss = OrderLogistics.query.filter(
        OrderLogistics.isdelete == False,
        OrderLogistics.OLsignStatus != LogisticsSignStatus.already_signed.value,
        OrderLogistics.OMid == OrderMain.OMid,
        OrderMain.isdelete == False,
        OrderMain.OMstatus == OrderMainStatus.wait_recv.value,
        OrderLogistics.updatetime <= time_now - timedelta(days=1)
    ).all()
    current_app.logger.info('获取物流信息, 共{}条快递单'.format(len(order_logisticss)))
    for order_logistics in order_logisticss:
        with db.auto_commit():
            order_logistics = clogistic._get_logistics(order_logistics)


@celery.task(name='auto_confirm_order')
def auto_confirm_order():
    """已签收7天自动确认收货, 在物流跟踪上已经签收, 但是用户没有手动签收的订单"""
    from planet.models import OrderLogistics
    from planet.control.COrder import COrder
    cfs = ConfigSettings()
    auto_confirm_day = int(cfs.get_item('order_auto', 'auto_confirm_day'))
    time_now = datetime.now()
    corder = COrder()
    order_mains = OrderMain.query.filter(
        OrderMain.isdelete == False,
        OrderMain.OMstatus == OrderMainStatus.wait_recv.value,
        OrderLogistics.OMid == OrderMain.OMid,
        OrderLogistics.isdelete == False,
        OrderLogistics.OLsignStatus == LogisticsSignStatus.already_signed.value,
        OrderLogistics.updatetime <= time_now - timedelta(days=auto_confirm_day)
        ).all()
    current_app.logger.info('自动确认收货, 共{}个订单'.format(len(order_mains)))
    for order_main in order_mains:
        with db.auto_commit():
            order_main = corder._confirm(order_main=order_main)

@celery.task()
def auto_agree_task(avid):
    current_app.logger.info('avid is {}'.format(avid))
    from planet.control.CApproval import CApproval
    cp = CApproval()
    with db.auto_commit():
        approval = Approval.query.filter(
            Approval.isdelete == False,
            Approval.AVstatus == ApplyStatus.wait_check.value,
            Approval.AVid == avid
        ).first()
        if approval:
            current_app.logger.info('5分钟自动同意')
            current_app.logger.info(dict(approval))
        else:
            current_app.logger.info('该审批已提前处理')
        try:
            cp.agree_action(approval)
            approval.AVstatus = ApplyStatus.agree.value
        except NotFound :
            current_app.logger.info('审批流状态有误')
            # 如果不存在的商品, 需要将审批流失效
            approval.AVstatus = ApplyStatus.cancle.value
        db.session.add(approval)


@celery.task()
def auto_cancle_order(omids):
    for omid in omids:
        from planet.control.COrder import COrder
        order_main = OrderMain.query.filter(OrderMain.isdelete == False,
                                            OrderMain.OMstatus == OrderMainStatus.wait_pay.value,
                                            OrderMain.OMid == omid).first()
        if not order_main:
            current_app.logger.info('订单已支付或已取消')
            return
        current_app.logger.info('订单自动取消{}'.format(dict(order_main)))
        corder = COrder()
        corder._cancle(order_main)


if __name__ == '__main__':
    from planet import create_app
    app = create_app()
    with app.app_context():
        # fetch_share_deal()
        # create_settlenment()
        auto_confirm_order()
