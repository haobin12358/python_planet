# -*- coding: utf-8 -*-
import os
import threading
import uuid
from datetime import date, timedelta, datetime
from decimal import Decimal

import requests
from flask import current_app
from flask_celery import Celery
from sqlalchemy import cast, Date, extract, func, or_, and_

from planet.common.error_response import NotFound
from planet.common.share_stock import ShareStock
from planet.common.welfare_lottery import WelfareLottery
from planet.config.cfgsetting import ConfigSettings
from planet.config.enums import OrderMainStatus, OrderFrom, UserCommissionStatus, ProductStatus, ApplyStatus, ApplyFrom, \
    SupplizerSettementStatus, LogisticsSignStatus, UserCommissionType, TrialCommodityStatus, TimeLimitedStatus, \
    CartFrom, CorrectNumType, GuessGroupStatus, GuessRecordStatus, GuessRecordDigits, MagicBoxJoinStatus, \
    ActivityDepositStatus, PlayStatus

from planet.extensions.register_ext import db
from planet.models import CorrectNum, GuessNum, GuessAwardFlow, ProductItems, OrderMain, OrderPart, OrderEvaluation, \
    Products, User, UserCommission, Approval, Supplizer, SupplizerSettlement, OrderLogistics, UserWallet, \
    FreshManFirstProduct, FreshManFirstApply, FreshManFirstSku, ProductSku, GuessNumAwardApply, GuessNumAwardProduct, \
    GuessNumAwardSku, MagicBoxApply, OutStock, TrialCommodity, SceneItem, ProductScene, ProductUrl, Coupon, CouponUser, \
    SupplizerDepositLog, TimeLimitedActivity, TimeLimitedProduct, TimeLimitedSku, Carts, IndexBanner, GuessGroup, \
    GuessRecord, GroupGoodsSku, GroupGoodsProduct, MagicBoxJoin, MagicBoxApplySku, ActivityDeposit, Play

celery = Celery()


@celery.task(name="fetch_share_deal")
def fetch_share_deal():
    """获取昨日的收盘"""
    with db.auto_commit():
        s_list = []
        share_stock = ShareStock()
        yesterday_result = share_stock.new_result()
        # yesterday = date.today() - timedelta(days=1)
        today = date.today()
        # 昨日结果
        db_today = CorrectNum.query.filter(
            cast(CorrectNum.CNdate, Date) == today,
            CorrectNum.CNtype == CorrectNumType.composite_index.value
        ).first()
        # if not db_today:  # 昨日
        if not db_today and yesterday_result:  # 今日
            # current_app.logger.info('写入昨日数据')
            current_app.logger.info('写入今日数据')
            correct_instance = CorrectNum.create({
                'CNid': str(uuid.uuid1()),
                'CNnum': yesterday_result,
                'CNdate': today
            })
            s_list.append(correct_instance)
            # 判断是否有猜对的
            # 更新逻辑之后不需要判断是否猜对
        #     guess_nums = GuessNum.query.filter_by({'GNnum': yesterday_result, 'GNdate': db_today}).all()
        #     for guess_num in guess_nums:
        #         exists_in_flow = GuessAwardFlow.query.filter_by_({'GNid': guess_num.GNid}).first()
        #         if not exists_in_flow:
        #             guess_award_flow_instance = GuessAwardFlow.create({
        #                 'GAFid': str(uuid.uuid4()),
        #                 'GNid': guess_num.GNid,
        #             })
        #             s_list.append(guess_award_flow_instance)
        if s_list:
            db.session.add_all(s_list)


@celery.task(name='welfare_lottery_3d')
def welfare_lottery_3d():
    """当日福彩3D开奖情况"""
    try:
        current_app.logger.info('>>> 获取今日福彩数据 <<<')
        with db.auto_commit():
            res = WelfareLottery().get_response()
            if not res:
                current_app.logger.error('今日无开奖数据')
                return
            today = res[0]
            issue = res[1]
            nums = ''.join(map(str, res[2:]))
            cn_instance = CorrectNum.create({'CNid': str(uuid.uuid1()),
                                             'CNnum': nums,
                                             'CNdate': today,
                                             'CNtype': CorrectNumType.lottery_3d.value,
                                             'CNissue': issue})
            db.session.add(cn_instance)
        current_app.logger.info('>>> 福彩数据为：{} <<<'.format(res))
    except Exception as e:
        current_app.logger.error('welfare_lottery_3d : {}'.format(e))
    finally:
        current_app.logger.info('>>> 获取福彩数据任务结束 <<<')


@celery.task(name='guess_group_draw')
def guess_group_draw():
    """拼团竞猜开奖"""
    from planet.control.COrder import COrder
    corder = COrder()
    now = datetime.now()
    zero_point, one_point, two_point, three_point = 0, 0, 0, 0
    try:
        current_app.logger.info('>>> 拼团今日开奖 <<<')

        # 获取正确结果
        correct_res = CorrectNum.query.filter(CorrectNum.isdelete == False,
                                              CorrectNum.CNtype == CorrectNumType.lottery_3d.value,
                                              CorrectNum.CNdate == now.date()
                                              ).first()
        if not correct_res or not correct_res.CNnum:
            current_app.logger.error('数据库中没有获取到正确结果')
        correct_num = correct_res.CNnum

        with db.auto_commit():
            timeout = GuessGroup.query.filter(GuessGroup.isdelete == False,
                                              GuessGroup.GGstatus == GuessGroupStatus.pending.value,
                                              GuessGroup.GGendtime < now)
            wait_draw = GuessGroup.query.filter(GuessGroup.isdelete == False,
                                                GuessGroup.GGstatus == GuessGroupStatus.waiting.value)
            guess_groups = timeout.union(wait_draw).all()
            current_app.logger.info('共有{}个拼团待处理'.format(len(guess_groups)))
            for group in guess_groups:
                if group.GGstatus == GuessGroupStatus.pending.value:  # 超时还在拼团状态
                    group.GGstatus = GuessGroupStatus.failed.value  # 拼团状态改为失败
                    grs = GuessRecord.query.filter_by(isdelete=False,
                                                      GGid=group.GGid,
                                                      GRstatus=GuessRecordStatus.valid.value).all()
                    if len(grs) > 3:
                        current_app.logger.error('该团 GGid:{} 有效竞猜记录为 {}'.format(group.GGid, len(grs)))
                        continue
                    for gr in grs:
                        order_main = OrderMain.query.filter(OrderMain.isdelete == False,
                                                            OrderMain.OMid == gr.OMid,
                                                            OrderMain.OMstatus == OrderMainStatus.wait_send.value,
                                                            ).first()
                        if not order_main:
                            current_app.logger.error('竞猜记录 GRid:{} 未找到相应订单'.format(gr.GRid))
                            continue
                        corder._cancle(order_main)  # 更改主单状态为取消 退库存 减销量
                        order_part = OrderPart.query.filter_by_(OMid=order_main.OMid).first()

                        # 增加佣金记录，更改用户钱包余额
                        group_refund_to_wallet(order_main, order_part)
                else:  # 等待开奖的
                    group.GGstatus = GuessGroupStatus.completed.value  # 拼团状态改为完成
                    group.GGcorrectNum = correct_num  # 记录当期的正确结果
                    grs = GuessRecord.query.filter_by(isdelete=False,
                                                      GGid=group.GGid,
                                                      GRstatus=GuessRecordStatus.valid.value).all()
                    if len(grs) > 3:
                        current_app.logger.error('该团异常 GGid:{} ，竞猜记录数量为 {}'.format(group.GGid, len(grs)))
                        continue

                    # 该团猜中数字位数
                    correct_count = 0
                    for gr in grs:
                        if gr.GRdigits == GuessRecordDigits.hundredDigits.value:
                            if str(gr.GRnumber) == str(correct_num[0]):
                                correct_count += 1
                        elif gr.GRdigits == GuessRecordDigits.tenDigits.value:
                            if str(gr.GRnumber) == str(correct_num[1]):
                                correct_count += 1
                        elif gr.GRdigits == GuessRecordDigits.singleDigits.value:
                            if str(gr.GRnumber) == str(correct_num[2]):
                                correct_count += 1
                        else:
                            continue

                    if correct_count == 1:
                        current_app.logger.info('该团{}猜中一位数'.format(group.GGid))
                        one_point += 1
                        for gri in grs:
                            order_main = OrderMain.query.filter(OrderMain.isdelete == False,
                                                                OrderMain.OMid == gri.OMid,
                                                                OrderMain.OMstatus == OrderMainStatus.wait_send.value,
                                                                ).first()
                            if not order_main:
                                current_app.logger.error('竞猜记录 GRid:{} 未找到相应订单'.format(gr.GRid))
                                continue
                            order_part = OrderPart.query.filter_by_(OMid=order_main.OMid).first()
                            gg_sku = GroupGoodsSku.query.filter_by_(GSid=order_part.SKUid).first()
                            price = round(float(order_part.OPsubTrueTotal - gg_sku.SKUFirstLevelPrice), 2)
                            current_app.logger.info(f'price = {order_part.OPsubTrueTotal}-{gg_sku.SKUFirstLevelPrice}')
                            if price > 0:  # 退钱
                                current_app.logger.info('GGid {} 退钱 {}'.format(group.GGid, price))
                                group_refund_to_wallet(order_main, order_part, price=price)
                                # 退钱后更改订单中的实付金额，防止申请售后时 退钱过多
                                order_main.OMtrueMount = gg_sku.SKUFirstLevelPrice
                                order_part.OPsubTrueTotal = gg_sku.SKUFirstLevelPrice
                    elif correct_count == 2:
                        current_app.logger.info('该团{}猜中两位数'.format(group.GGid))
                        two_point += 1
                        for gri in grs:
                            order_main = OrderMain.query.filter(OrderMain.isdelete == False,
                                                                OrderMain.OMid == gri.OMid,
                                                                OrderMain.OMstatus == OrderMainStatus.wait_send.value,
                                                                ).first()
                            if not order_main:
                                current_app.logger.error('竞猜记录 GRid:{} 未找到相应订单'.format(gr.GRid))
                                continue
                            order_part = OrderPart.query.filter_by_(OMid=order_main.OMid).first()
                            gg_sku = GroupGoodsSku.query.filter_by_(GSid=order_part.SKUid).first()
                            price = round(float(order_part.OPsubTrueTotal - gg_sku.SKUSecondLevelPrice), 2)
                            current_app.logger.info(f'price = {order_part.OPsubTrueTotal}-{gg_sku.SKUSecondLevelPrice}')
                            if price > 0:  # 退钱
                                current_app.logger.info('GGid {} 退钱 {}'.format(group.GGid, price))
                                group_refund_to_wallet(order_main, order_part, price=price)
                                # 退钱后更改订单中的实付金额，防止申请售后时 退钱过多
                                order_main.OMtrueMount = gg_sku.SKUSecondLevelPrice
                                order_part.OPsubTrueTotal = gg_sku.SKUSecondLevelPrice
                    elif correct_count == 3:
                        current_app.logger.info('该团{}猜中三位数'.format(group.GGid))
                        three_point += 1
                        for gri in grs:
                            order_main = OrderMain.query.filter(OrderMain.isdelete == False,
                                                                OrderMain.OMid == gri.OMid,
                                                                OrderMain.OMstatus == OrderMainStatus.wait_send.value,
                                                                ).first()
                            if not order_main:
                                current_app.logger.error('竞猜记录 GRid:{} 未找到相应订单'.format(gr.GRid))
                                continue
                            order_part = OrderPart.query.filter_by_(OMid=order_main.OMid).first()
                            gg_sku = GroupGoodsSku.query.filter_by_(GSid=order_part.SKUid).first()
                            price = round(float(order_part.OPsubTrueTotal - gg_sku.SKUThirdLevelPrice), 2)
                            current_app.logger.info(f'price = {order_part.OPsubTrueTotal}-{gg_sku.SKUThirdLevelPrice}')
                            if price > 0:  # 退钱
                                current_app.logger.info('GGid {} 退钱 {}'.format(group.GGid, price))
                                group_refund_to_wallet(order_main, order_part, price=price)
                                # 退钱后更改订单中的实付金额，防止申请售后时 退钱过多
                                order_main.OMtrueMount = gg_sku.SKUThirdLevelPrice
                                order_part.OPsubTrueTotal = gg_sku.SKUThirdLevelPrice
                    elif correct_count == 0:
                        zero_point += 1
                    else:
                        current_app.logger.error('异常团 GPid {} 待开奖，但猜中记录数为{}'.format(group.GGid, correct_count))
    except Exception as e:
        current_app.logger.error('>>> 拼团开奖错误: {}<<<'.format(e))
    finally:
        current_app.logger.info('>>> 拼团开奖结束，共有{}个团猜中一位数，{}个团猜中两位，'
                                '{}个团全中，{}团全未中<<<'.format(one_point, two_point, three_point, zero_point))


def group_refund_to_wallet(order_main, order_part, price=None):
    """拼团退款到钱包"""
    current_app.logger.info(f'竞猜订单退还押金 OMid {order_main.OMid}')
    if not price:
        price = order_part.OPsubTrueTotal
    user_commision_dict = {
        'UCid': str(uuid.uuid1()),
        'UCcommission': Decimal(price).quantize(Decimal('0.00')),
        'USid': order_main.USid,
        'UCstatus': UserCommissionStatus.in_account.value,
        'UCtype': UserCommissionType.group_refund.value,
        'PRtitle': f'[拼团押金]{order_part.PRtitle}',
        'SKUpic': order_part.PRmainpic,
        'OMid': order_part.OMid,
        'OPid': order_part.OPid
    }
    db.session.add(UserCommission.create(user_commision_dict))

    user_wallet = UserWallet.query.filter_by_(USid=order_main.USid).first()

    if user_wallet:
        user_wallet.UWbalance = Decimal(str(user_wallet.UWbalance or 0)) + Decimal(str(price))
        user_wallet.UWtotal = Decimal(str(user_wallet.UWtotal or 0)) + Decimal(str(price))
        user_wallet.UWcash = Decimal(str(user_wallet.UWcash or 0)) + Decimal(str(price))
        db.session.add(user_wallet)
    else:
        user_wallet_instance = UserWallet.create({
            'UWid': str(uuid.uuid1()),
            'USid': order_main.USid,
            'UWbalance': Decimal(price).quantize(Decimal('0.00')),
            'UWtotal': Decimal(price).quantize(Decimal('0.00')),
            'UWcash': Decimal(price).quantize(Decimal('0.00')),
            # 'UWexpect': user_commision.UCcommission,
            'CommisionFor': ApplyFrom.user.value
        })
        db.session.add(user_wallet_instance)


@celery.task(name='paid_but_not_guess_refund')
def paid_but_not_guess_refund():
    """拼团竞猜 未竞猜的订单 退还押金"""
    current_app.logger.info('>>> 今日未竞猜订单退还 <<<')
    count = 0
    try:
        with db.auto_commit():
            from planet.control.COrder import COrder
            corder = COrder()
            oms = OrderMain.query.filter(OrderMain.isdelete == False,
                                         OrderMain.OMstatus == OrderMainStatus.wait_send.value,
                                         OrderMain.OMfrom == OrderFrom.guess_group.value,
                                         ).all()
            for om in oms:
                gr = GuessRecord.query.filter(GuessRecord.isdelete == False,
                                              GuessRecord.GRstatus == GuessRecordStatus.valid.value,
                                              GuessRecord.OMid == om.OMid).first()
                if not gr and not om.OMinRefund:  # 订单未关联任何有效记录且不在售后中
                    current_app.logger.info(f'OMid {om.OMid} 未关联有效竞猜')
                    op = OrderPart.query.filter_by_(OMid=om.OMid).first()
                    # 退钱
                    group_refund_to_wallet(om, op)
                    # 取消订单
                    corder._cancle(om)
                    count += 1
    except Exception as e:
        current_app.logger.error('>>> 未竞猜订单退还错误: {}<<<'.format(e))
    finally:
        current_app.logger.info(f'>>> 未竞猜订单退还结束，共修改 {count} 条数据<<<')


@celery.task(name='magic_box_join_expired')
def magic_box_join_expired():
    """礼盒到期 未下单 退还押金"""
    current_app.logger.info('>>> 检测到期后仍未下单的盒子 <<<')
    count = 0
    today = datetime.now().date()
    try:
        with db.auto_commit():
            from planet.control.COrder import COrder
            corder = COrder()
            magic_box_joins = MagicBoxJoin.query.filter(MagicBoxJoin.isdelete == False,
                                                        MagicBoxJoin.MBJstatus == MagicBoxJoinStatus.pending.value,
                                                        MagicBoxJoin.MBSendtime < today,
                                                        MagicBoxJoin.OMid.is_(None)
                                                        ).all()
            current_app.logger.info('共 {} 个盒子 到期后未下单'.format(len(magic_box_joins)))
            for mbj in magic_box_joins:
                deposit = ActivityDeposit.query.filter(ActivityDeposit.isdelete == False,
                                                       ActivityDeposit.ACDid == mbj.ACDid,
                                                       ActivityDeposit.ACDstatus == ActivityDepositStatus.valid.value
                                                       ).first()
                if deposit:
                    current_app.logger.info('存在有效押金ACDid:{}，开始退还'.format(deposit.ACDid))
                    # 押金状态改为已退还
                    deposit.update({'ACDstatus': ActivityDepositStatus.revert.value})
                    db.session.add(deposit)

                    # 开始退押金
                    price = deposit.ACDdeposit
                    user_commision_dict = {
                        'UCid': str(uuid.uuid1()),
                        'UCcommission': Decimal(price).quantize(Decimal('0.00')),
                        'USid': deposit.USid,
                        'UCstatus': UserCommissionStatus.in_account.value,
                        'UCtype': UserCommissionType.box_deposit.value,
                        'PRtitle': '[礼盒押金]{}'.format(mbj.PRtitle),
                        'SKUpic': mbj.PRmainpic,
                        # 'OMid': order_part.OMid,
                        # 'OPid': order_part.OPid
                    }
                    db.session.add(UserCommission.create(user_commision_dict))

                    user_wallet = UserWallet.query.filter_by_(USid=deposit.USid).first()

                    if user_wallet:
                        user_wallet.UWbalance = Decimal(str(user_wallet.UWbalance or 0)) + Decimal(str(price))
                        user_wallet.UWtotal = Decimal(str(user_wallet.UWtotal or 0)) + Decimal(str(price))
                        user_wallet.UWcash = Decimal(str(user_wallet.UWcash or 0)) + Decimal(str(price))
                        db.session.add(user_wallet)
                    else:
                        user_wallet_instance = UserWallet.create({
                            'UWid': str(uuid.uuid1()),
                            'USid': deposit.USid,
                            'UWbalance': Decimal(price).quantize(Decimal('0.00')),
                            'UWtotal': Decimal(price).quantize(Decimal('0.00')),
                            'UWcash': Decimal(price).quantize(Decimal('0.00')),
                            # 'UWexpect': user_commision.UCcommission,
                            'CommisionFor': ApplyFrom.user.value
                        })
                        db.session.add(user_wallet_instance)

                    count += 1
                else:
                    current_app.logger.error('该盒子未找到有效押金记录 MBJid:{}'.format(mbj.MBJid))

    except Exception as e:
        current_app.logger.error('>>> 到期未下单盒子退还押金错误: {}<<<'.format(e))
    finally:
        current_app.logger.info(f'>>> 到期未下单盒子退还押金结束，共修改 {count} 条数据<<<')


@celery.task(name='guess_group_expired_revert')
def guess_group_expired_revert():
    """过期拼团商品退还库存"""
    current_app.logger.info(">>> 开始过期拼团商品退还库存 <<<")
    from planet.control.COrder import COrder
    corder = COrder()
    today = datetime.now().date()
    count, pending_count = 0, 0
    try:
        with db.auto_commit():
            group_product = GroupGoodsProduct.query.filter(GroupGoodsProduct.isdelete == False,
                                                           GroupGoodsProduct.GPstatus == ApplyStatus.agree.value,
                                                           GroupGoodsProduct.GPday < today).all()
            current_app.logger.info('共{}个已到期'.format(len(group_product)))
            for gp in group_product:
                continue_group = GuessGroup.query.filter(GuessGroup.isdelete == False,
                                                         GuessGroup.GGstatus.in_((GuessGroupStatus.pending.value,
                                                                                  GuessGroupStatus.waiting.value)),
                                                         GuessGroup.GPid == gp.GPid
                                                         ).first()
                if continue_group:
                    current_app.logger.info(f'商品GPid:{gp.GPid} 仍有进行中的拼团 {continue_group.GGid}')
                    pending_count += 1
                    continue

                current_app.logger.info(f'拼团商品GPid:{gp.GPid} 开始退还')
                gps = GroupGoodsSku.query.filter_by_(GPid=gp.GPid).all()
                for gsku in gps:
                    corder._update_stock(int(gsku.GSstock), skuid=gsku.SKUid)
                count += 1
                gp.GPstatus = ApplyStatus.shelves.value  # 已退库存的商品改为下架状态
    except Exception as e:
        current_app.logger.error('>>> 过期拼团商品退还库存错误: {}<<<'.format(e))
    finally:
        current_app.logger.info(f'>>> 过期拼团商品退还库存结束，共{count}个商品退还库存，仍有{pending_count}个商品在进行拼团<<<')


@celery.task(name='magic_box_expired_revert')
def magic_box_expired_revert():
    """过期魔术礼盒"""
    current_app.logger.info(">>> 开始过期拼团商品退还库存 <<<")
    from planet.control.COrder import COrder
    corder = COrder()
    today = datetime.now().date()
    count, pending_count = 0, 0
    try:
        with db.auto_commit():
            magic_box_applys = MagicBoxApply.query.filter(MagicBoxApply.isdelete == False,
                                                          MagicBoxApply.MBAstatus == ApplyStatus.agree.value,
                                                          MagicBoxApply.MBAday < today,
                                                          ).all()
            current_app.logger.info('> 到期的魔盒商品有 {} 个 < '.format(len(magic_box_applys)))
            for magic_box_apply in magic_box_applys:
                pending_box = MagicBoxJoin.query.filter(MagicBoxJoin.isdelete == False,
                                                        MagicBoxJoin.MBJstatus == MagicBoxJoinStatus.pending.value,
                                                        MagicBoxJoin.MBAid == magic_box_apply.MBAid,
                                                        MagicBoxJoin.MBSendtime >= today).first()
                if pending_box:
                    current_app.logger.info(f'商品MBAid:{magic_box_apply.MBAid} 仍有未完成盒子MBJid:{pending_box.MBJid}')
                    pending_count += 1
                    continue
                current_app.logger.info(' 魔术礼盒MBAid : {} 开始退还'.format(magic_box_apply.MBAid))
                mbs = MagicBoxApplySku.query.filter(MagicBoxApplySku.isdelete == False,
                                                    MagicBoxApplySku.MBAid == magic_box_apply.MBAid).all()
                for mbsku in mbs:
                    corder._update_stock(int(mbsku.MBSstock), skuid=mbsku.SKUid)
                count += 1
                magic_box_apply.MBAstatus = ApplyStatus.shelves.value  # 已退回库存的商品改为已下架
    except Exception as e:
        current_app.logger.error('>>> 过期魔盒商品退还库存错误: {}<<<'.format(e))
    finally:
        current_app.logger.info(f'>>> 退还库存结束，共{count}个商品退还库存，仍有{pending_count}个商品仍有在分享的盒子<<<')


@celery.task(name='auto_evaluate')
def auto_evaluate():
    """超时自动评价订单"""
    try:
        cfs = ConfigSettings()
        limit_time = cfs.get_item('order_auto', 'auto_evaluate_day')
        # limit_time = 7
        time_now = datetime.now()
        with db.auto_commit():
            s_list = []
            current_app.logger.info(">>>>>>  开始检测超过{0}天未评价的商品订单  <<<<<<".format(limit_time))
            from planet.control.COrder import COrder
            corder = COrder()
            count = 0
            wait_comment_order_mains = OrderMain.query.filter(OrderMain.isdelete == False,
                                                              OrderMain.OMstatus == OrderMainStatus.wait_comment.value,
                                                              # OrderMain.OMfrom.in_(
                                                              #     [OrderFrom.carts.value, OrderFrom.product_info.value]),
                                                              OrderMain.updatetime <= time_now - timedelta(
                                                                  days=int(limit_time))
                                                              )  # 所有超过天数 待评价 的商品订单

            complete_comment_order_mains = OrderMain.query.join(OrderLogistics, OrderLogistics.OMid == OrderMain.OMid,
                                                                ).filter(OrderMain.isdelete == False,
                                                                         OrderMain.OMstatus == OrderMainStatus.complete_comment.value,
                                                                         OrderLogistics.isdelete == False,
                                                                         OrderLogistics.OLsignStatus == LogisticsSignStatus.already_signed.value,
                                                                         OrderLogistics.updatetime <= time_now - timedelta(
                                                                             days=int(limit_time))
                                                                         )  # 所有已评价的订单
            order_mains = wait_comment_order_mains.union(complete_comment_order_mains).all()

            if not order_mains:
                current_app.logger.info(">>>>>>  没有超过{0}天未评价的商品订单  <<<<<<".format(limit_time))

            else:
                for order_main in order_mains:
                    order_parts = OrderPart.query.filter_by_(OMid=order_main.OMid).all()  # 主单下所有副单

                    ol = OrderLogistics.query.filter_by(OMid=order_main.OMid, isdelete=False).first()
                    if not ol or ol.OLsignStatus != LogisticsSignStatus.already_signed.value:
                        continue

                    for order_part in order_parts:
                        if order_part.OPisinORA is True:
                            continue
                        user = User.query.filter_by(USid=order_main.USid, isdelete=False).first()

                        exist_evaluation = OrderEvaluation.query.filter_by_(OPid=order_part.OPid).first()
                        if exist_evaluation:
                            current_app.logger.info(
                                ">>>>>  该副单已存在评价, OPid : {}, OMid : {}, OMstatus : {}".format(order_part.OPid,
                                                                                              order_part.OMid,
                                                                                              order_main.OMstatus))
                            corder._fresh_commsion_into_count(order_part)  # 佣金到账
                            if user:  # 防止因用户不存在,进入下个方法报错停止
                                corder._tosalesvolume(order_main.OMtrueMount, user.USid)  # 销售额统计
                            count += 1
                            continue  # 已评价的订单只进行销售量统计、佣金到账，跳过下面的评价步骤

                        corder._fresh_commsion_into_count(order_part)  # 佣金到账

                        if user and order_main.OMfrom not in [OrderFrom.trial_commodity.value,
                                                              OrderFrom.integral_store.value]:

                            usname, usheader = user.USname, user.USheader
                            corder._tosalesvolume(order_main.OMtrueMount, user.USid)  # 销售额统计
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
                        # 商品总体评分变化
                        try:
                            product_info = Products.query.filter_by_(PRid=order_part.PRid).first_("商品不存在")
                            scores = [oe.OEscore for oe in
                                      OrderEvaluation.query.filter(OrderEvaluation.PRid == product_info.PRid,
                                                                   OrderEvaluation.isdelete == False).all()]
                            average_score = round(((float(sum(scores)) + float(5.0)) / (len(scores) + 1)) * 2)
                            Products.query.filter_by(PRid=order_part.PRid).update({'PRaverageScore': average_score})
                        except Exception as e:
                            current_app.logger.info("更改商品评分失败, 商品可能已被删除；Update Product Score ERROR ：{}".format(e))

                    # 更改主单状态为已完成
                    change_status = OrderMain.query.filter_by_(OMid=order_main.OMid).update(
                        {'OMstatus': OrderMainStatus.ready.value})
                    if change_status:
                        current_app.logger.info(">>>>>>  主单状态更改成功 OMid : {}  <<<<<<".format(str(order_main.OMid)))
                    else:
                        current_app.logger.info(">>>>>>  主单状态更改失败 OMid : {}  <<<<<<".format(str(order_main.OMid)))
            if s_list:
                db.session.add_all(s_list)
            current_app.logger.info(">>>>>> 自动评价任务结束，共更改{}条数据  <<<<<<".format(count))
    except Exception as err:
        current_app.logger.error(">>>>>> 自动评价任务出错 : {}  <<<<<<".format(err))


@celery.task(name='deposit_to_account')
def deposit_to_account():
    """试用商品押金到账"""
    try:
        with db.auto_commit():
            current_app.logger.info("-->  开始检测押金是否到期  <--")
            deposits = UserCommission.query.filter(UserCommission.isdelete == False,
                                                   UserCommission.UCstatus == UserCommissionStatus.preview.value,
                                                   UserCommission.UCtype == UserCommissionType.deposit.value,
                                                   UserCommission.UCendTime <= datetime.now()
                                                   ).all()
            current_app.logger.info("-->  共有{}个订单的押金已到期  <--".format(len(deposits)))
            for deposit in deposits:
                current_app.logger.info("-->  'UCid‘ : {}  <--".format(deposit.UCid))
                user_name = getattr(User.query.filter(User.USid == deposit.USid).first(), 'USname', '') or None
                # 更改佣金状态
                deposit.UCstatus = UserCommissionStatus.in_account.value
                db.session.add(deposit)
                # 用户钱包
                user_wallet = UserWallet.query.filter(UserWallet.isdelete == False,
                                                      UserWallet.USid == deposit.USid,
                                                      UserWallet.CommisionFor == deposit.CommisionFor
                                                      ).first()
                if user_wallet:
                    current_app.logger.info("-->  用户 ‘{}’ 已有钱包账户  <--".format(user_name))
                    user_wallet.UWbalance = Decimal(str(user_wallet.UWbalance or 0)) + Decimal(
                        str(deposit.UCcommission or 0))
                    user_wallet.UWtotal = Decimal(str(user_wallet.UWtotal or 0)) + Decimal(str(deposit.UCcommission))
                    user_wallet.UWcash = Decimal(str(user_wallet.UWcash or 0)) + Decimal(str(deposit.UCcommission))
                    current_app.logger.info("此次到账佣金{}；该用户现在账户余额：{}； 账户总额{}； 可提现余额{}".format(
                        deposit.UCcommission, user_wallet.UWbalance, user_wallet.UWtotal, user_wallet.UWcash))
                    db.session.add(user_wallet)
                else:
                    current_app.logger.info("-->  用户 ‘{}’ 没有钱包账户，正在新建  <--".format(user_name))
                    user_wallet_instance = UserWallet.create({
                        'UWid': str(uuid.uuid1()),
                        'USid': deposit.USid,
                        'UWbalance': deposit.UCcommission,
                        'UWtotal': deposit.UCcommission,
                        'UWcash': deposit.UCcommission,
                        'CommisionFor': deposit.CommisionFor
                    })
                    current_app.logger.info("此次到账佣金{}；".format(deposit.UCcommission))
                    db.session.add(user_wallet_instance)
                current_app.logger.info(" {}".format('=' * 30))
            current_app.logger.info(" >>>>>  押金到账任务结束  <<<<<")
    except Exception as e:
        current_app.logger.error("押金到账任务出错 : {}；".format(e))


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
                current_app.logger.info(
                    "-->  存在有评价，主单已删除或来自活动订单，OMid为{0}, OMfrom为{1}  <--".format(str(oe.OMid), str(om_info.OMfrom)))
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
        from planet.control.COrder import COrder
        corder = COrder()
        today = datetime.now()
        pre_month = date(year=today.year, month=today.month, day=1) - timedelta(days=1)
        tomonth_22 = date(year=today.year, month=today.month, day=22)
        pre_month_22 = date(year=pre_month.year, month=pre_month.month, day=22)
        for su in su_list:
            # today = datetime.strptime('2019-04-22 00:00:00', '%Y-%m-%d %H:%M:%S')
            su_comiission = db.session.query(func.sum(UserCommission.UCcommission)).filter(
                UserCommission.USid == su.SUid,
                UserCommission.isdelete == False,
                UserCommission.UCstatus == UserCommissionStatus.in_account.value,
                UserCommission.CommisionFor == ApplyFrom.supplizer.value,
                # or_(
                #     and_(
                #         cast(UserCommission.createtime, Date) < tomonth_22,
                #         cast(UserCommission.createtime, Date) >= pre_month_22,),
                #     and_(
                cast(UserCommission.updatetime, Date) < tomonth_22,
                cast(UserCommission.updatetime, Date) >= pre_month_22,
                # ))
            ).first()
            ss_total = su_comiission[0] or 0
            ss = SupplizerSettlement.create({
                'createtime': today,
                'updatetime': today,
                'SSid': str(uuid.uuid1()),
                'SUid': su.SUid,
                'SSdealamount': float('%.2f' % float(ss_total)),
                'SSstatus': SupplizerSettementStatus.checking.value
            })
            db.session.add(ss)
            db.session.flush()
            corder._create_settlement_excel(su.SUid, ss)
        from planet.config.secret import BASEDIR
        sourcepath = os.path.join(BASEDIR, 'img', 'xls', str(today.year), str(today.month))
        tarfilename = os.path.join(sourcepath, '{}-{}.tar.gz'.format(today.year, today.month))
        corder.create_tar(tarfilename, sourcepath)


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


@celery.task(name='check_for_update')
def check_for_update(*args, **kwargs):
    current_app.logger.info('args is {}, kwargs is {}'.format(args, kwargs))
    from planet.control.CUser import CUser
    if 'users' in kwargs:
        users = kwargs.get('users')
    elif 'usid' in kwargs:
        users = User.query.filter(User.isdelete == False, User.USid == kwargs.get('usid')).all()
    elif args:
        users = args
    else:
        users = User.query.filter(
            User.isdelete == False,
            User.CommisionLevel <= 5,
            User.USlevel == 2
        ).all()
    cuser = CUser()
    for user in users:
        with db.auto_commit():
            cuser._check_for_update(user=user)
            db.session.add(user)


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
        except NotFound:
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


@celery.task()
def cancel_scene_association(psid):
    current_app.logger.info('--> 限时场景到期任务 PSid: {} <-- '.format(psid))
    try:
        with db.auto_commit():
            scene = ProductScene.query.filter(ProductScene.PSid == psid, ProductScene.PStimelimited == True,
                                              ProductScene.isdelete == False).first_('场景不存在或非限时')
            sitids = [sitem.ITid for sitem in SceneItem.query.filter(SceneItem.PSid == scene.PSid,
                                                                     SceneItem.isdelete == False).all()]
            for itid in sitids:
                if SceneItem.query.filter(SceneItem.ITid == itid, SceneItem.PSid != psid,
                                          SceneItem.isdelete == False).first():
                    continue
                else:
                    current_app.logger.info('--> 标签"{}"只有此场景有关联，同时删除标签下的商品关联 <-- '.format(itid))
                    ProductItems.query.filter(ProductItems.ITid == itid, ProductItems.isdelete == False).delete_()

            SceneItem.query.filter(SceneItem.PSid == scene.PSid).delete_()  # 删除该场景下的标签关联

    except Exception as e:
        current_app.logger.error('限时场景到期任务出错 >>> {}'.format(e))
    current_app.logger.info('--> 限时场景到期任务结束 <-- ')


@celery.task(name='expired_scene_association')
def expired_scene_association():
    """对于修改过结束时间的限时场景，到期后定时清理关联"""
    current_app.logger.info('--> 限时场景取消关联定时任务 <-- ')
    try:
        with db.auto_commit():
            scenes = ProductScene.query.filter(ProductScene.PSendtime < datetime.now(),
                                               ProductScene.createtime != ProductScene.updatetime,
                                               ProductScene.PStimelimited == True,
                                               ProductScene.isdelete == False).all()
            current_app.logger.info('--> 共有{}个被修改过的限时场景过期 <-- '.format(len(scenes)))
            for scene in scenes:
                sitids = [sitem.ITid for sitem in SceneItem.query.filter(SceneItem.PSid == scene.PSid,
                                                                         SceneItem.isdelete == False).all()]
                current_app.logger.info('--> 限时场景id : {} <-- '.format(scene.PSid))
                for itid in sitids:
                    if SceneItem.query.filter(SceneItem.ITid == itid, SceneItem.PSid != scene.PSid,
                                              SceneItem.isdelete == False).first():
                        continue
                    else:
                        current_app.logger.info('--> 标签"{}"只有此场景有关联，同时删除标签下的商品关联 <-- '.format(itid))
                        ProductItems.query.filter(ProductItems.ITid == itid, ProductItems.isdelete == False).delete_()

                SceneItem.query.filter(SceneItem.PSid == scene.PSid).delete_()  # 删除该场景下的标签关联

    except Exception as e:
        current_app.logger.error('限时场景到期任务出错 >>> {}'.format(e))
    current_app.logger.info('--> 限时场景取消关联定时任务结束 <-- ')


@celery.task(name='event_expired_revert')
def event_expired_revert():
    """过期活动商品返还库存"""
    current_app.logger.error('>>> 活动商品到期返回库存检测 <<< ')
    from planet.control.COrder import COrder
    corder = COrder()
    today = date.today()

    try:
        with db.auto_commit():
            # 新人首单
            fresh_man_products = FreshManFirstProduct.query.join(
                FreshManFirstApply, FreshManFirstApply.FMFAid == FreshManFirstProduct.FMFAid
            ).filter_(FreshManFirstApply.FMFAstatus == ApplyStatus.agree.value,
                      FreshManFirstApply.AgreeStartime < today,
                      FreshManFirstApply.AgreeEndtime < today,
                      FreshManFirstApply.isdelete == False,
                      FreshManFirstProduct.isdelete == False,
                      Products.PRid == FreshManFirstProduct.PRid,
                      Products.isdelete == False,
                      ).all()  # 已经到期的新人首单活动
            current_app.logger.info('>>> 到期的新人首单有 {} 个 <<< '.format(len(fresh_man_products)))
            for fresh_man_pr in fresh_man_products:
                # 到期后状态改为已下架
                current_app.logger.info(' 过期新人首单进行下架 >> FMFAid : {} '.format(fresh_man_pr.FMFAid))
                FreshManFirstApply.query.filter(FreshManFirstApply.FMFAid == fresh_man_pr.FMFAid,
                                                FreshManFirstApply.AgreeStartime < today,
                                                FreshManFirstApply.AgreeEndtime < today,
                                                ).update({'FMFAstatus': ApplyStatus.shelves.value})
                fresh_man_skus = FreshManFirstSku.query.filter_by_(FMFPid=fresh_man_pr.FMFPid).all()
                for fresh_man_sku in fresh_man_skus:
                    # 加库存
                    current_app.logger.info(' 恢复库存的新人首单SKUid >> {} '.format(fresh_man_sku.SKUid))
                    corder._update_stock(fresh_man_sku.FMFPstock, skuid=fresh_man_sku.SKUid)

            # 猜数字
            guess_num_products = GuessNumAwardProduct.query.join(
                GuessNumAwardApply, GuessNumAwardApply.GNAAid == GuessNumAwardProduct.GNAAid
            ).filter(GuessNumAwardApply.isdelete == False,
                     GuessNumAwardProduct.isdelete == False,
                     GuessNumAwardApply.GNAAstatus == ApplyStatus.agree.value,
                     GuessNumAwardApply.AgreeStartime < today,
                     GuessNumAwardApply.AgreeEndtime < today,
                     Products.PRid == GuessNumAwardProduct.PRid,
                     Products.isdelete == False,
                     ).all()  # # 已经到期的猜数字活动
            current_app.logger.info('>>> 到期的猜数字有 {} 个 <<< '.format(len(guess_num_products)))
            for guess_num_pr in guess_num_products:
                # 到期后状态改为已下架
                current_app.logger.info(' 过期猜数字进行下架 >> GNAAid : {} '.format(guess_num_pr.GNAAid))
                GuessNumAwardApply.query.filter(GuessNumAwardApply.GNAAid == guess_num_pr.GNAAid,
                                                GuessNumAwardApply.AgreeStartime < today,
                                                GuessNumAwardApply.AgreeEndtime < today,
                                                ).update({'GNAAstatus': ApplyStatus.shelves.value})
                gna_skus = GuessNumAwardSku.query.filter_by_(GNAPid=guess_num_pr.GNAPid).all()
                for gna_sku in gna_skus:
                    # 加库存
                    current_app.logger.info(' 恢复库存的猜数字SKUid >> {} '.format(gna_sku.SKUid))
                    corder._update_stock(gna_sku.SKUstock, skuid=gna_sku.SKUid)

            # 试用商品
            trialcommoditys = TrialCommodity.query.filter(TrialCommodity.TCstatus == TrialCommodityStatus.upper.value,
                                                          TrialCommodity.AgreeStartTime < today,
                                                          TrialCommodity.AgreeEndTime < today,
                                                          TrialCommodity.isdelete == False
                                                          ).all()
            current_app.logger.info('>>> 到期的试用商品有 {} 个 <<< '.format(len(trialcommoditys)))
            for trialcommodity in trialcommoditys:
                current_app.logger.info(' 过期试用商品进行下架 >> TCid : {} '.format(trialcommodity.TCid))
                trialcommodity.update({'TCstatus': TrialCommodityStatus.reject.value})

            #  试用商品不占用普通商品库存

            # # 限时活动
            # tla_list = TimeLimitedActivity.query.filter(
            #     TimeLimitedActivity.isdelete == False,
            #     TimeLimitedActivity.TLAstatus <= TimeLimitedStatus.publish.value,
            #     cast(TimeLimitedActivity.TLAendTime, Date) < today).all()
            # current_app.logger.info('开始退还限时活动的库存 本日到期限时活动 {} 个 '.format(len(tla_list)))
            # for tla in tla_list:
            #     tlp_list = TimeLimitedProduct.query.filter(
            #         TimeLimitedProduct.isdelete == False,
            #         TimeLimitedProduct.TLAstatus >= ApplyStatus.wait_check.value,
            #         TimeLimitedProduct.TLAid == tla.TLAid).all()
            #     tla.TLAstatus = TimeLimitedStatus.end.value
            #     current_app.logger.info('过期活动 tlaid = {} 过期商品有 {} '.format(tla.TLAid, len(tlp_list)))
            #     for tlp in tlp_list:
            #         current_app.logger.info('过期限时活动商品 TLPid ： {}'.format(tlp.TLPid))
            #         tls = TimeLimitedSku.query.filter(
            #             TimeLimitedSku.isdelete == False,
            #             TimeLimitedSku.TLPid == tlp.TLPid).all()
            #         corder._update_stock(tls.TLSstock, skuid=tls.SKUid)

    except Exception as e:
        current_app.logger.error('活动商品到期返回库存出错 >>> {}'.format(e))
    current_app.logger.info('--> 活动商品到期返回库存检测任务结束 <-- ')


# 图片下载格式配置文件
contenttype_config = {
    r'image/jpeg': r'.jpg',
    r'image/pnetvue': r'.net',
    r'image/tiff': r'.tif',
    r'image/fax': r'.fax',
    r'image/gif': r'.gif',
    r'image/png': r'.png',
    r'image/vnd.rn-realpix': r'.rp',
    r'image/vnd.wap.wbmp': r'.wbmp',
}


@celery.task()
def get_url_local(url_list):
    """
    将url转置为图片保存到自己服务器上
    :param url:
    :return:
    """

    def _get_path(fold):
        """获取服务器上文件路径"""
        time_now = datetime.now()
        year = str(time_now.year)
        month = str(time_now.month)
        day = str(time_now.day)
        filepath = os.path.join(current_app.config['BASEDIR'], 'img', fold, year, month, day)
        file_db_path = os.path.join('/img', fold, year, month, day)
        if not os.path.isdir(filepath):
            os.makedirs(filepath)
        return filepath, file_db_path

    current_app.logger.info('start 去重 {}'.format(datetime.now()))
    url_list = {}.fromkeys(url_list).keys()  # 去重
    current_app.logger.info('end  去重 {}'.format(datetime.now()))
    with db.auto_commit():
        for url in url_list:
            current_app.logger.info('start get url {} time {}'.format(url, datetime.now()))
            content = requests.get(url)
            current_app.logger.info('end get url ')
            url_type = contenttype_config.get(content.headers._store.get('content-type')[-1])
            current_app.logger.info('get url type = {}'.format(url_type))
            if not url_type:
                current_app.logger.info('当前url {} 获取失败 或url 不是图片格式'.format(url))
                return
            filename = str(uuid.uuid1()) + url_type

            filepath, filedbpath = _get_path('backup')
            filedbname = os.path.join(filedbpath, filename)
            filename = os.path.join(filepath, filename)

            with open(filename, 'wb') as head:
                head.write(content.content)

            current_app.logger.info('save url end ')
            # 建立远端图片与服务器图片关系
            current_app.logger.info('start insert into database')
            prurl_instance = ProductUrl.query.with_for_update(read=False, nowait=True).filter(
                ProductUrl.PUurl == url, ProductUrl.isdelete == False).first()
            if prurl_instance:
                current_app.logger.info(
                    '开始更新远端url {}  原path 是 {}'.format(url, prurl_instance.PUdir))
                # 创建数据库锁
                # lock = threading.Lock()
                old_path = os.path.join(current_app.config['BASEDIR'], prurl_instance.PUdir)
                if os.path.isfile(old_path):
                    os.remove(old_path)

                prurl_instance.PUdir = filedbname

                current_app.logger.info('更新后的path 是 {}'.format(filedbname))
            else:
                prurl_instance = ProductUrl.create({
                    'PUid': str(uuid.uuid1()),
                    'PUurl': url,
                    'PUdir': filedbname
                })

                db.session.add(prurl_instance)
            db.session.flush()
            current_app.logger.info('end get url {}'.format(datetime.now()))
    current_app.logger.info('end dbsession')


@celery.task(name='return_coupon_deposite')
def return_coupon_deposite():
    now = datetime.now()
    yesterday = now - timedelta(days=1)
    current_app.logger.info('开始返回供应商发布优惠券剩余押金')
    with db.auto_commit():
        coupon_list = Coupon.query.filter(
            Coupon.isdelete == False,
            Coupon.COvalidEndTime > yesterday,
            Coupon.COvalidEndTime <= now,
            Coupon.SUid != None
        ).all()
        current_app.logger.info('今天有 {} 优惠券到期'.format(len(coupon_list)))
        for coupon in coupon_list:

            su = Supplizer.query.filter(Supplizer.isdelete == False, Supplizer.SUid == coupon.SUid).first()
            if not su:
                continue
            unused_count = CouponUser.query.filter(
                CouponUser.isdelete == False, CouponUser.COid == coupon.COid, CouponUser.UCalreadyUse == False).count()
            current_app.logger.info('get 优惠券 {} 未使用的 {} 未领取的 {}'.format(
                coupon.COid, unused_count, coupon.COremainNum))
            coupon_remain = (Decimal(str(coupon.COremainNum or 0)) + Decimal(str(unused_count or 0))) * Decimal(
                str(coupon.COsubtration))
            # 押金返回
            su_remain = Decimal(str(su.SUdeposit or 0))
            current_app.logger.info('开始返回供应商 {} 押金 该供应商押金剩余 {} 本次增加 {} 修改后为 {} '.format(
                su.SUname, su_remain, coupon_remain, su_remain + coupon_remain
            ))
            su.SUdeposit = su_remain + coupon_remain
            # 增加押金变更记录
            sdl = SupplizerDepositLog.create({
                "SDLid": str(uuid.uuid1()),
                'SUid': su.SUid,
                'SDLnum': coupon_remain,
                'SDafter': su.SUdeposit,
                'SDbefore': su_remain,
                'SDLacid': 'system'
            })
            db.session.add(sdl)
            db.session.flush()
    current_app.logger.info('返回供应商押金结束')


@celery.task()
def end_timelimited(tlaid):
    current_app.logger.info('开始修改限时活动为结束，并且退还库存给商品')
    from planet.control.COrder import COrder
    tla = TimeLimitedActivity.query.filter(
        TimeLimitedActivity.isdelete == False, TimeLimitedActivity.TLAid == tlaid).first()
    if not tla:
        current_app.logger.info('已删除该活动 任务结束')
        return

    tlps = TimeLimitedProduct.query.filter(
        TimeLimitedProduct.isdelete == False, TimeLimitedProduct.TLAid == tlaid).all()
    with db.auto_commit():
        # 获取原sku属性
        corder = COrder()
        for tlp in tlps:
            tls_old = TimeLimitedSku.query.filter(
                TimeLimitedSku.TLPid == tlp.TLPid,
                TimeLimitedSku.isdelete == False,
                TimeLimitedProduct.isdelete == False,
            ).all()
            # 获取原商品属性
            product = Products.query.filter_by(PRid=tlp.PRid, isdelete=False).first()
            if not product:
                current_app.logger.info('退还库存的商品已删除 库存保留在活动商品里 prid = {}'.format(tlp.PRid))
                continue
            # 遍历原sku 将库存退出去
            for sku in tls_old:
                sku_instance = ProductSku.query.filter_by(
                    isdelete=False, PRid=product.PRid, SKUid=sku.SKUid).first_('商品sku信息不存在')
                corder._update_stock(int(sku.TLSstock), product, sku_instance)
                Carts.query.filter_by(SKUid=sku.SKUid, CAfrom=CartFrom.time_limited.value).delete_()
        tla.TLAstatus = TimeLimitedStatus.end.value
        # 删除轮播图
        IndexBanner.query.filter_by(
            IBpic=tla.TLAtopPic,
            isdelete=False
        ).delete_()
    current_app.logger.info('修改限时活动为结束，并且退还库存给商品 结束')


@celery.task()
def start_timelimited(tlaid):
    current_app.logger.info('开始修改限时活动为开始')
    tla = TimeLimitedActivity.query.filter(
        TimeLimitedActivity.isdelete == False, TimeLimitedActivity.TLAid == tlaid).first()
    if not tla:
        current_app.logger.info('已删除该活动 任务结束')
        return
    if tla.TLAstatus == TimeLimitedStatus.abort.value:
        current_app.logger.info('已中止的活动不自动开启')
        return

    with db.auto_commit():
        tla.TLAstatus = TimeLimitedStatus.starting.value
    current_app.logger.info('修改限时活动为开始 结束')


@celery.task()
def start_play(plid):
    current_app.logger.info('开始修改活动为开始 plid {}'.format(plid))
    current_app.logger.info('开始修改活动为开始 plid {}'.format(type(plid)))
    with db.auto_commit():
        play = Play.query.filter_by(PLid=plid, isdelete=False).first()
        if play:
            current_app.logger.info('活动存在 plid {}'.format(plid))
            if play.PLstatus == PlayStatus.close.value:
                current_app.logger.info('活动已关闭，不再重复开启')
                return
            play.PLstatus = PlayStatus.activity.value

    current_app.logger.info('结束修改活动为开始 plid {}'.format(plid))


@celery.task()
def end_play(plid):
    current_app.logger.info('开始修改活动为开始 plid {}'.format(plid))
    with db.auto_commit():
        play = Play.query.filter_by(PLid=plid, isdelete=False).first()
        if play:
            current_app.logger.info('活动存在 plid {}'.format(plid))
            play.PLstatus = PlayStatus.close.value

    current_app.logger.info('结束修改活动为开始 plid {}'.format(plid))


if __name__ == '__main__':
    from planet import create_app

    app = create_app()
    with app.app_context():
        # event_expired_revert()
        # deposit_to_account()
        # fetch_share_deal()
        # create_settlenment()
        # auto_evaluate()
        # check_for_update()
        # auto_confirm_order()
        # get_url_local(['http://m.qpic.cn/psb?/V13fqaNT3IKQx9/mByjunzSxxDcxQXgrrRTAocPeZ4jnvHnPE56c8l3zpU!/b/dL8AAAAAAAAA&bo=OAQ4BAAAAAARFyA!&rf=viewer_4'] * 102)
        # return_coupon_deposite()
        # welfare_lottery_3d()
        guess_group_draw()
