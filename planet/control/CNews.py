# -*- coding: utf-8 -*-
import json
import re
import uuid
from datetime import datetime

from flask import request, current_app
from planet.common.error_response import ParamsError, SystemError, NotFound, AuthorityError, StatusError, TokenError
from planet.common.params_validates import parameter_required
from planet.common.success_response import Success
from planet.common.token_handler import token_required, is_tourist, admin_required, get_current_user, get_current_admin, \
    is_admin, is_supplizer
from planet.config.enums import ItemType, NewsStatus, ApprovalType, ApplyFrom, ApplyStatus
from planet.control.BaseControl import BASEAPPROVAL
from planet.control.CCoupon import CCoupon
from planet.extensions.register_ext import db
from planet.models import News, NewsImage, NewsVideo, NewsTag, Items, UserSearchHistory, NewsFavorite, NewsTrample, \
    Products, CouponUser, Admin, ProductBrand, User, NewsChangelog, Supplizer, Approval
from planet.models import NewsComment, NewsCommentFavorite
from planet.models.trade import Coupon
from planet.service.SNews import SNews
from sqlalchemy import or_, and_


class CNews(BASEAPPROVAL):
    def __init__(self):
        self.snews = SNews()
        self.empty = ['', {}, [], [''], None]

    def get_all_news(self):
        if is_tourist():
            usid = None
            tourist = 1
        elif is_admin():
            usid = request.user.id
            admin = self._check_admin(usid)
            current_app.logger.info('Admin {0} is geting all news'.format(admin.ADname))
            tourist = 'admin'
        elif is_supplizer():
            usid = request.user.id
            sup = self._check_supplizer(usid)
            current_app.logger.info('Supplizer {0} is geting all news'.format(sup.SUname))
            tourist = 'supplizer'
        else:
            usid = request.user.id
            user = self.snews.get_user_by_id(usid)
            current_app.logger.info('User {0} is geting all news'.format(user.USname))
            tourist = 0

        args = parameter_required(('page_num', 'page_size'))
        itid = args.get('itid')
        kw = args.get('kw', '').split() or ['']  # 关键词
        nestatus = args.get('nestatus') or 'usual'
        nestatus = getattr(NewsStatus, nestatus).value
        userid = None
        if str(itid) == 'mynews':
            if not usid:
                raise TokenError('未登录')
            userid = usid
            itid = None
            nestatus = None
        elif is_supplizer():
            userid = usid
        news_list = self.snews.get_news_list([
            or_(and_(*[News.NEtitle.contains(x) for x in kw]), and_(*[News.NEtext.contains(x) for x in kw])),
            NewsTag.ITid == itid,
            News.NEstatus == nestatus,
            News.USid == userid
        ])
        for news in news_list:
            news.fields = ['NEid', 'NEtitle', 'NEpageviews']
            # 添加发布者信息
            auther = news.USname or ''
            if news.NEfrom == ApplyFrom.platform.value:
                news.fill('authername', '{} (管理员)'.format(auther))
            elif news.NEfrom == ApplyFrom.supplizer.value:
                news.fill('authername', '{} (供应商)'.format(auther))
            else:
                news.fill('authername', '{} (用户)'.format(auther))
            if news.NEstatus == NewsStatus.usual.value and not (is_admin() or is_supplizer()):
                self.snews.update_pageviews(news.NEid)  # 增加浏览量
            # 显示点赞状态
            if usid:
                is_favorite = self.snews.news_is_favorite(news.NEid, usid)
                favorite = 1 if is_favorite else 0
                is_own = 1 if news.USid == usid else 0
            else:
                favorite = 0
                is_own = 0
            news.fill('is_favorite', favorite)
            news.fill('is_own', is_own)
            # 显示审核状态
            if userid or is_admin():
                news_status = news.NEstatus
                news.fill('zh_nestatus', NewsStatus(news_status).zh_value)
                news.fill('nestatus', NewsStatus(news_status).name)
                if news_status == NewsStatus.refuse.value:
                    reason = news.NErefusereason or '因内容不符合规定，审核未通过，建议修改后重新发布'
                    news.fill('refuse_info', reason)
            commentnumber = self.snews.get_news_comment_count(news.NEid)
            news.fill('commentnumber', commentnumber)
            favoritnumber = self.snews.get_news_favorite_count(news.NEid)
            news.fill('favoritnumber', favoritnumber)
            video = self.snews.get_news_video(news.NEid)
            if video and not news.NEmainpic:
                video_source = video['NVvideo']
                showtype = 'video'
                video_thumbnail = video['NVthumbnail']
                dur_time = video['NVduration']
                news.fill('video', video_source)
                news.fill('videothumbnail', video_thumbnail)
                news.fill('videoduration', dur_time)
            elif news.NEmainpic:
                showtype = 'picture'
                news.fill('mainpic', news['NEmainpic'])
            else:
                image_list = self.snews.get_news_images(news.NEid)
                if image_list:
                    mainpic = image_list[0]['NIimage']
                    showtype = 'picture'
                    news.fill('mainpic', mainpic)
                else:
                    netext = news.NEtext[:120]
                    news.fill('netext', netext)
                    showtype = 'text'
            news.fill('showtype', showtype)
            if news.USheader:
                usheader = news['USheader']
            else:
                usinfo = self.fill_user_info(news.USid)
                usheader = usinfo['USheader']
            news.fill('usheader', usheader)
        # 增加搜索记录
        if kw not in self.empty and usid:
            with self.snews.auto_commit() as s:
                instance = UserSearchHistory.create({
                    'USHid': str(uuid.uuid4()),
                    'USid': request.user.id,
                    'USHname': ' '.join(kw),
                    'USHtype': 10
                })
                s.add(instance)
        return Success(data=news_list).get_body(istourst=tourist)

    def get_news_content(self):
        """资讯详情"""
        if is_tourist():
            usid = None
            tourist = 1
        elif is_admin():
            usid = request.user.id
            admin = self._check_admin(usid)
            current_app.logger.info('Admin {0} is geting news content'.format(admin.ADname))
            tourist = 'admin'
        elif is_supplizer():
            usid = request.user.id
            sup = self._check_supplizer(usid)
            current_app.logger.info('Supplizer {0} is geting news content'.format(sup.SUname))
            tourist = 'supplizer'
        else:
            usid = request.user.id
            user = self.snews.get_user_by_id(usid)
            current_app.logger.info('User {0} is geting news content'.format(user.USname))
            tourist = 0
        args = parameter_required(('neid',))
        neid = args.get('neid')
        news = self.snews.get_news_content({'NEid': neid})
        news.fields = ['NEid', 'NEtitle', 'NEpageviews', 'NEtext', 'NEmainpic', 'NEisrecommend']

        if re.match(r'^[01]$', str(tourist)):  # 是普通用户或游客
            if news.NEstatus == NewsStatus.usual.value:
                self.snews.update_pageviews(news.NEid)  # 增加浏览量
            else:
                if news.USid != usid:  # 前台查看‘我发布的’ 需要获取非正常状态情况
                    raise StatusError('该资讯正在审核中，请耐心等待')
                else:
                    pass

        if usid:
            is_own = 1 if news.USid == usid else 0
            is_favorite = self.snews.news_is_favorite(neid, usid)
            favorite = 1 if is_favorite else 0
            is_trample = self.snews.news_is_trample(neid, usid)
            trample = 1 if is_trample else 0
        else:
            is_own = 0
            favorite = 0
            trample = 0
        news.fill('is_own', is_own)
        news.fill('is_favorite', favorite)
        news.fill('is_trample', trample)
        # news_author = self.snews.get_user_by_id(news.USid)
        if news.USheader and news.USname:
            news_author = {'usname': news.USname, 'usheader': news['USheader']}
        else:
            news_author = User.query.filter_by(USid=news.USid).first()
            if news_author:
                news_author.fields = ['USname', 'USheader']
            else:
                news_author = {'usname': '神秘的客官', 'usheader': ''}
        news.fill('author', news_author)
        news.fill('createtime', news.createtime)
        commentnumber = self.snews.get_news_comment_count(neid)
        news.fill('commentnumber', commentnumber)
        favoritnumber = self.snews.get_news_favorite_count(neid)
        news.fill('favoritnumber', favoritnumber)
        tramplenumber = self.snews.get_news_trample_count(neid)
        news.fill('tramplenumber', tramplenumber)
        image_list = self.snews.get_news_images(neid)
        if image_list:
            [image.hide('NEid') for image in image_list]
        news.fill('image', image_list)
        video = self.snews.get_news_video(neid)
        if video:
            video.hide('NEid')
            news.fill('video', video)
        tags = self.snews.get_item_list((NewsTag.NEid == neid,))
        if tags:
            [tag.hide('PSid') for tag in tags]
        news.fill('items', tags)
        # 关联的优惠券
        coids = news.COid
        if coids:
            coupon_info = []
            coid_list = json.loads(coids)
            for coid in coid_list:
                coupon = Coupon.query.filter_by_(COid=coid).first()
                if not coupon:
                    continue
                coupon_detail = CCoupon()._title_subtitle(coupon)
                coupon.fill('title_subtitle', coupon_detail)
                coupon_user = CouponUser.query.filter_by_({'USid': usid, 'COid': coupon.COid}).first() if usid else False
                coupon.fill('ready_collected', bool(coupon_user))
                coupon_info.append(coupon)
            news.fill('coupon', coupon_info)
        # 关联的商品
        prids = news.PRid
        if prids:
            prid_info = []
            prid_list = json.loads(prids)
            for prid in prid_list:
                product = Products.query.filter_by_(PRid=prid).first()
                if not product:
                    continue
                product.fields = ['PRid', 'PRtitle', 'PRprice', 'PRlinePrice', 'PRmainpic']
                brand = ProductBrand.query.filter_by_(PBid=product.PBid).first()
                product.fill('brand', brand)
                prid_info.append(product)
            news.fill('product', prid_info)

        return Success(data=news).get_body(istourist=tourist)

    def get_news_banner(self):
        """获取资讯图轮播"""
        banner_list = []
        recommend_news = self.snews.get_news_list_by_filter({'NEisrecommend': True, 'NEstatus': NewsStatus.usual.value})
        for news in recommend_news:
            if news.NEmainpic:
                banner = news['NEmainpic']
            else:
                img_list = self.snews.get_news_images(news.NEid)
                if img_list:
                    banner = img_list[0]['NIimage']
                else:
                    continue
            data = {
                'neid': news.NEid,
                'mainpic': banner
            }
            banner_list.append(data)
        return Success(data=banner_list)

    @token_required
    def create_news(self):
        """创建资讯"""
        user = get_current_user()
        admin = get_current_admin()
        if user:
            usid, usname, usheader = user.USid, user.USname, user.USheader
            current_app.logger.info('User {0} create a news'.format(usname))
            nefrom = ApplyFrom.user.value
        elif admin:
            usid, usname, usheader = admin.ADid, admin.ADname, admin.ADheader
            current_app.logger.info('Admin {0} create a news'.format(usname))
            nefrom = ApplyFrom.platform.value
        elif is_supplizer():
            supplizer = Supplizer.query.filter_by_(SUid=request.user.id).first()
            usid, usname, usheader = supplizer.SUid, supplizer.SUname, supplizer.SUheader
            current_app.logger.info('Supplizer {0} create a news'.format(usname))
            nefrom = ApplyFrom.supplizer.value
        else:
            raise TokenError('用户不存在')
        data = parameter_required(('netitle', 'netext', 'items', 'source'))
        neid = str(uuid.uuid1())
        images = data.get('images')  # [{niimg:'url', nisort:1},]
        items = data.get('items')  # ['item1', 'item2']
        video = data.get('video')  # {nvurl:'url', nvthum:'url'}
        coupon = data.get('coupon')  # ['coid1', 'coid2', 'coid3']
        product = data.get('product')  # ['prid1', 'prid2']
        mainpic = data.get('nemainpic')
        coupon = json.dumps(coupon) if coupon not in self.empty else None
        product = json.dumps(product) if product not in self.empty else None
        isrecommend = data.get('neisrecommend', 0)
        isrecommend = True if str(isrecommend) == '1' else False
        if user:
            isrecommend = False
        if isrecommend and not mainpic:
            raise ParamsError("被推荐的资讯必须上传封面图")
        with self.snews.auto_commit() as s:
            session_list = []
            news_info = News.create({
                'NEid': neid,
                'USid': usid,
                'NEtitle': data.get('netitle'),
                'NEtext': data.get('netext'),
                'NEstatus': NewsStatus.auditing.value,
                'NEsource': data.get('source'),
                'NEmainpic': mainpic,
                'NEisrecommend': isrecommend,
                'COid': coupon,
                'PRid': product,
                'USname': usname,
                'USheader': usheader,
                'NEfrom': nefrom
            })
            session_list.append(news_info)
            if images not in self.empty:
                if len(images) > 4:
                    raise ParamsError('最多只能上传四张图片')
                for image in images:
                    news_image_info = NewsImage.create({
                        'NIid': str(uuid.uuid1()),
                        'NEid': neid,
                        'NIimage': image.get('niimg'),
                        'NIsort': image.get('nisort')
                    })
                    session_list.append(news_image_info)
            if video not in self.empty:
                parameter_required(('nvurl', 'nvthum', 'nvdur'), datafrom=video)
                duration_time = video.get('nvdur') or "10"
                second = int(duration_time[-2:])
                if second < 3:
                    raise ParamsError('上传视频时间不能少于3秒')
                elif second > 59:
                    raise ParamsError('上传视频时间不能大于1分钟')
                news_video_info = NewsVideo.create({
                    'NVid': str(uuid.uuid1()),
                    'NEid': neid,
                    'NVvideo': video.get('nvurl'),
                    'NVthumbnail': video.get('nvthum'),
                    'NVduration': video.get('nvdur')
                })
                session_list.append(news_video_info)
            if items not in self.empty:
                for item in items:
                    s.query(Items).filter_by_({'ITid': item, 'ITtype': ItemType.news.value}).first_('指定标签不存在')
                    news_item_info = NewsTag.create({
                        'NTid': str(uuid.uuid1()),
                        'NEid': neid,
                        'ITid': item
                    })
                    session_list.append(news_item_info)
            s.add_all(session_list)

            # 添加到审批流
        super().create_approval('topublish', usid, neid, nefrom)
        return Success('添加成功', {'neid': neid})

    @admin_required
    def update_news(self):
        """修改资讯"""
        adid = request.user.id
        admin = Admin.query.filter_by_(ADid=adid).first_('没有该管理账号信息')
        current_app.logger.info("Admin {} update news".format(admin.ADname))
        data = parameter_required(('neid',))
        neid = data.get('neid')
        images = data.get('image')  # [{niimg:'url', nisort:1},]
        items = data.get('items')  # ['item1', 'item2']
        video = data.get('video')  # {nvurl:'url', nvthum:'url'}
        coupon = data.get('coupon') or []  # ['coid1', 'coid2', 'coid3']
        product = data.get('product') or []  # ['prid1', 'prid2']

        isrecommend = data.get('neisrecommend')
        isrecommend = True if str(isrecommend) == '1' else False
        operation = list()

        if not isinstance(coupon, list):
            raise ParamsError('coupon格式错误 , 应为["coid1", "coid2"]')
        elif not isinstance(product, list):
            raise ParamsError('product格式错误 , 应为["prid1", "prid2"]')
        coupon = json.dumps(coupon) if coupon not in self.empty else None
        product = json.dumps(product) if product not in self.empty else None

        with self.snews.auto_commit() as s:
            s.query(News).filter_by_(NEid=neid, NEstatus=NewsStatus.refuse.value).first_('只能修改已下架状态的资讯')
            session_list = []
            news_info = {
                'NEtitle': data.get('netitle'),
                'NEtext': data.get('netext'),
                'NEstatus': NewsStatus.auditing.value,
                # 'NEsource': 'web',
                'COid': coupon,
                'PRid': product,
                'NEmainpic': data.get('nemainpic'),
                'NEisrecommend': isrecommend,
            }
            news_info = {k: v for k, v in news_info.items() if v is not None}
            s.query(News).filter_by_(NEid=neid).update(news_info)
            operation.append('修改基础内容')
            if images not in self.empty:
                if len(images) > 4:
                    raise ParamsError('最多只能上传四张图片')
                exist_niid = [img.NIid for img in s.query(NewsImage).filter_by_(NEid=neid).all()]
                for image in images:
                    if 'niid' in image:
                        exist_niid.remove(image.get('niid'))
                    else:
                        news_image_info = NewsImage.create({
                            'NIid': str(uuid.uuid1()),
                            'NEid': neid,
                            'NIimage': image.get('niimage'),
                            'NIsort': image.get('nisort')
                        })
                        operation.append(' / 增加图片')
                        session_list.append(news_image_info)
                [s.query(NewsImage).filter_by(NIid=old_niid).delete_() for old_niid in exist_niid]  # 删除原有的但修改后不需要的图片

            if video not in self.empty:
                parameter_required(('nvvideo', 'nvthumbnail', 'nvduration'), datafrom=video)
                duration_time = video.get('nvdur') or "10"
                second = int(duration_time[-2:])
                if second < 3:
                    raise ParamsError('上传视频时间不能少于3秒')
                elif second > 59:
                    raise ParamsError('上传视频时间不能大于1分钟')
                if 'nvid' in video:
                    pass
                else:
                    s.query(NewsVideo).filter_by(NEid=neid).delete_()  # 删除原有的视频
                    news_video_info = NewsVideo.create({
                        'NVid': str(uuid.uuid1()),
                        'NEid': neid,
                        'NVvideo': video.get('nvvideo'),
                        'NVthumbnail': video.get('nvthumbnail'),
                        'NVduration': video.get('nvduration')
                    })
                    operation.append(' / 增加视频')
                    session_list.append(news_video_info)
            if items not in self.empty:
                s.query(NewsTag).filter_by(NEid=neid).delete_()  # 删除原有的标题
                for item in items:
                    s.query(Items).filter_by_({'ITid': item, 'ITtype': ItemType.news.value}).first_('指定标签不存在')
                    news_item_info = NewsTag.create({
                        'NTid': str(uuid.uuid1()),
                        'NEid': neid,
                        'ITid': item
                    })
                    session_list.append(news_item_info)

            # 记录修改日志
            changelog = NewsChangelog.create({
                'NCLid': str(uuid.uuid1()),
                'NEid': neid,
                'ADid': adid,
                'NCLoperation': operation,
            })
            session_list.append(changelog)
            s.add_all(session_list)
            # 添加到审批流
            super().create_approval('topublish', adid, neid, ApplyFrom.platform.value)
        return Success('修改成功', {'neid': neid})

    def del_news(self):
        """删除资讯"""
        if is_tourist():
            raise TokenError()
        elif is_admin():
            usid = request.user.id
            admin = self._check_admin(usid)
            current_app.logger.info('Admin {0} delete news'.format(admin.ADname))
        elif is_supplizer():
            usid = request.user.id
            sup = self._check_supplizer(usid)
            current_app.logger.info('Supplizer {0} delete news'.format(sup.SUname))
        else:
            usid = request.user.id
            user = self.snews.get_user_by_id(usid)
            current_app.logger.info('User {0} is delete news'.format(user.USname))
        data = parameter_required(('neid',))
        neids = data.get('neid')
        with db.auto_commit():
            for neid in neids:
                news = News.query.filter_by_(NEid=neid).first_('未找到该资讯或已被删除')
                if is_admin():
                    if news.NEstatus != NewsStatus.refuse.value:
                        raise StatusError('只能删除已下架状态的资讯')
                else:
                    if news.USid != usid:
                        raise StatusError('只能删除自己发布的资讯')
                News.query.filter_by(NEid=neid, isdelete=False).delete_()
                NewsImage.query.filter_by(NEid=neid).delete_()  # 删除图片
                NewsVideo.query.filter_by(NEid=neid).delete_()  # 删除视频
                NewsTag.query.filter_by(NEid=neid).delete_()  # 删除标签关联
                NewsComment.query.filter_by(NEid=neid).delete_()  # 删除评论
                NewsFavorite.query.filter_by(NEid=neid).delete_()  # 删除点赞
                NewsTrample.query.filter_by(NEid=neid).delete_()  # 删除点踩
                # 如果在审核中，同时取消在进行的审批流
                if news.NEstatus == NewsStatus.auditing:
                    approval_info = Approval.query.filter_by_(AVcontent=neid, AVstartid=news.USid,
                                                              AVstatus=ApplyStatus.wait_check.value).first()
                    approval_info.AVstatus = ApplyStatus.cancle.value
        return Success('删除成功', {'neid': neids})

    @token_required
    def news_favorite(self):
        """资讯点赞/踩"""
        usid = request.user.id
        if usid:
            user = self.snews.get_user_by_id(usid)
            current_app.logger.info('User {0} is favorite/trample news'.format(user.USname))
        data = parameter_required(('neid', 'tftype'))
        neid = data.get('neid')
        news = self.snews.get_news_content({'NEid': neid})
        if news.NEstatus != NewsStatus.usual.value:
            raise StatusError('该资讯当前状态不允许点赞')
        tftype = data.get('tftype')  # {1:点赞, 0:点踩}
        if not re.match(r'^[01]$', str(tftype)):
            raise ParamsError('tftype, 参数异常')
        msg = '已取消'
        is_favorite = self.snews.news_is_favorite(neid, usid)
        is_trample = self.snews.news_is_trample(news.NEid, usid)

        if str(tftype) == '1':
            if not is_favorite:
                if is_trample:
                    # raise StatusError('请取消踩后再赞')
                    self.snews.cancel_trample(neid, usid)  # 改为自动取消
                with self.snews.auto_commit() as s:
                    news_favorite = NewsFavorite.create({
                        'NEFid': str(uuid.uuid1()),
                        'NEid': neid,
                        'USid': usid
                    })
                    s.add(news_favorite)
                msg = '已赞同'
            else:
                cancel_favorite = self.snews.cancel_favorite(neid, usid)
                if not cancel_favorite:
                    raise SystemError('服务器繁忙')
        else:
            if not is_trample:
                if is_favorite:
                    # raise StatusError('请取消赞后再踩')
                    self.snews.cancel_favorite(neid, usid)
                with self.snews.auto_commit() as sn:
                    news_trample = NewsTrample.create({
                        'NETid': str(uuid.uuid1()),
                        'NEid': neid,
                        'USid': usid
                    })
                    sn.add(news_trample)
                msg = '已反对'
            else:
                cancel_trample = self.snews.cancel_trample(neid, usid)
                if not cancel_trample:
                    raise SystemError('服务器繁忙')
        favorite = self.snews.news_is_favorite(neid, usid)
        favorite = 1 if favorite else 0
        favorite_count = self.snews.get_news_favorite_count(neid)
        trample = self.snews.news_is_trample(neid, usid)
        trample = 1 if trample else 0
        trample_count = self.snews.get_news_trample_count(neid)
        return Success(message=msg, data={'neid': neid, 'is_favorite': favorite, 'is_trample': trample,
                                          'favorite_count': favorite_count, 'trample_count': trample_count
                                          })

    def get_news_comment(self):
        """获取资讯评论"""
        if not is_tourist():
            usid = request.user.id
            if usid:
                user = self.snews.get_user_by_id(usid)
                current_app.logger.info('User {0} is get news comment'.format(user.USname))
                tourist = 0
        else:
            usid = None
            tourist = 1
        args = parameter_required(('neid', 'page_num', 'page_size'))
        neid = args.get('neid')
        news_comments = self.snews.get_news_comment((NewsComment.NEid == neid, NewsComment.isdelete == False,
                                                     NewsComment.NCparentid.is_(None), NewsComment.NCrootid.is_(None)))
        comment_total_count = NewsComment.query.filter(NewsComment.NEid == neid, NewsComment.isdelete == False).count()
        for news_comment in news_comments:
            self._get_one_comment(news_comment, neid, usid)
        return Success(data=news_comments).get_body(comment_count=comment_total_count, istourist=tourist)

    def _get_one_comment(self, news_comment, neid, usid=None):
        reply_comments = NewsComment.query.filter(NewsComment.NEid == neid,
                                                  NewsComment.isdelete == False,
                                                  NewsComment.NCrootid == news_comment.NCid
                                                  ).order_by(NewsComment.createtime.desc()).all()
        reply_count = NewsComment.query.filter(NewsComment.NEid == neid, NewsComment.isdelete == False,
                                               NewsComment.NCrootid == news_comment.NCid).count()
        favorite_count = NewsCommentFavorite.query.filter_by_(NCid=news_comment.NCid).count()
        for reply_comment in reply_comments:
            if reply_comment.USname:
                re_user_name = reply_comment.USname
            else:
                re_user = self.fill_user_info(reply_comment.USid)
                re_user_name = re_user['USname']
            reply_comment.fill('commentuser', re_user_name)
            replied_user = self.snews.get_comment_reply_user((NewsComment.NCid == reply_comment.NCparentid,))
            repliedusername = replied_user.USname if replied_user else '神秘的客官'
            if repliedusername == re_user_name:
                repliedusername = ''
            reply_comment.fill('replieduser', repliedusername)
            if usid:
                is_own = 1 if usid == reply_comment.USid else 0
            else:
                is_own = 0
            reply_comment.fill('is_own', is_own)
            reply_comment.hide('USid', 'USname', 'USheader')
        news_comment.fill('favorite_count', favorite_count)
        news_comment.fill('reply_count', reply_count)
        news_comment.fill('reply', reply_comments)
        news_comment.hide('USname', 'USheader', 'USid')
        if news_comment.USname and news_comment.USheader:
            user_info = {"usname": news_comment.USname, "usheader": news_comment['USheader']}
        else:
            user_info = self.fill_user_info(news_comment.USid)
            user_info = {k.lower(): v for k, v in dict(user_info).items()}  # 回复被删除的用户信息字段转小写
        news_comment.fill('user', user_info)
        if usid:
            is_favorite = self.snews.comment_is_favorite(news_comment.NCid, usid)
            favorite = 1 if is_favorite else 0
            is_own = 1 if usid == news_comment.USid else 0
        else:
            favorite = 0
            is_own = 0
        news_comment.fill('is_own', is_own)
        news_comment.fill('is_favorite', favorite)
        createtime = news_comment.createtime or datetime.now()
        # createtime = str(createtime).replace('-', '/')[:19]
        createtime = str(createtime)[:19]
        news_comment.fill('createtime', createtime)
        return news_comment

    @token_required
    def create_comment(self):
        usid = request.user.id
        user = self.snews.get_user_by_id(usid)
        usname, usheader = user.USname, user.USheader
        current_app.logger.info('User {0} is create comment'.format(user.USname))
        data = parameter_required(('neid', 'nctext'))
        neid = data.get('neid')
        new_info = self.snews.get_news_content({'NEid': neid, 'isdelete': False})
        if new_info.NEstatus != NewsStatus.usual.value:
            raise StatusError('该资讯当前状态不允许进行评论')
        ncid = data.get('ncid')
        comment_ncid = str(uuid.uuid1())
        reply_ncid = str(uuid.uuid1())
        # 直接评论资讯
        if ncid in self.empty:
            with self.snews.auto_commit() as nc:
                comment = NewsComment.create({
                    'NCid': comment_ncid,
                    'NEid': neid,
                    'USid': usid,
                    'USname': usname,
                    'USheader': usheader,
                    'NCtext': data.get('nctext'),
                })
                nc.add(comment)
            # 评论后返回刷新结果
            news_comment = NewsComment.query.filter_by_(NCid=comment_ncid).first()
            self._get_one_comment(news_comment, neid, usid)
        else:
            # 回复资讯评论
            ori_news_comment = NewsComment.query.filter(NewsComment.NCid == ncid, NewsComment.isdelete == False).first()
            if not ori_news_comment:
                raise NotFound('该评论已删除')
            ncrootid = ori_news_comment.NCrootid
            if not ncrootid:
                ncrootid = ncid
            with self.snews.auto_commit() as r:
                reply = NewsComment.create({
                    'NCid': reply_ncid,
                    'NEid': neid,
                    'USid': usid,
                    'USname': usname,
                    'USheader': usheader,
                    'NCtext': data.get('nctext'),
                    'NCparentid': ncid,
                    'NCrootid': ncrootid,
                })
                r.add(reply)
            # 评论后返回刷新结果
            news_comment = NewsComment.query.filter_by_(NCid=ncrootid).first()
            self._get_one_comment(news_comment, neid, usid)
        return Success('评论成功', data=news_comment)

    @token_required
    def comment_favorite(self):
        """评论点赞"""
        usid = request.user.id
        user = self.snews.get_user_by_id(usid)
        current_app.logger.info('get user is {0}, comment favorite'.format(user.USname))
        data = parameter_required(('ncid',))
        ncid = data.get('ncid')
        comment = NewsComment.query.filter(NewsComment.NCid == ncid,
                                           NewsComment.isdelete == False,
                                           NewsComment.NCrootid.is_(None)).first()
        if not comment:
            raise NotFound('不支持对回复点赞或评论已删除')
        is_favorite = self.snews.comment_is_favorite(ncid, usid)
        with self.snews.auto_commit() as s:
            if not is_favorite:
                comment_favorite = NewsCommentFavorite.create({
                    'NCFid': str(uuid.uuid1()),
                    'NCid': ncid,
                    'USid': usid
                })
                s.add(comment_favorite)
                msg = '已点赞'
            else:
                cancel_favorite = s.query(NewsCommentFavorite).filter(NewsCommentFavorite.NCid == ncid,
                                                                      NewsCommentFavorite.USid == usid
                                                                      ).delete_()
                if not cancel_favorite:
                    raise SystemError('服务器繁忙')
                msg = '已取消'
        favorite = self.snews.comment_is_favorite(ncid, usid)
        fav = 1 if favorite else 0
        return Success(msg, {'is_favorite': fav})

    @token_required
    def del_comment(self):
        """删除评论"""
        usid = request.user.id
        user = self.snews.get_user_by_id(usid)
        current_app.logger.info('get user is {0}, del news comment'.format(user.USname))
        data = parameter_required(('ncid',))
        ncid = data.get('ncid')
        comment = NewsComment.query.filter(NewsComment.NCid == ncid,
                                           NewsComment.isdelete == False
                                           ).first_('未找到该评论或已被删除')
        if usid == comment.USid:
            if comment.NCrootid is None:
                self.snews.del_comment(NewsComment.NCrootid == ncid)  # 删除评论下的回复
            del_comment = self.snews.del_comment(NewsComment.NCid == ncid)
            if not del_comment:
                raise SystemError('服务器繁忙')
        else:
            raise AuthorityError('只能删除自己发布的评论')
        return Success('删除成功', {'ncid': ncid})

    @staticmethod
    def _check_admin(usid):
        return Admin.query.filter_by_(ADid=usid).first_('管理员账号状态异常')

    @staticmethod
    def _check_supplizer(usid):
        return Supplizer.query.filter_by_(SUid=usid).first_('供应商信息错误')

    @staticmethod
    def fill_user_info(usid):
        try:
            usinfo = User.query.filter_by(USid=usid).first()
            usinfo.fields = ['USname', 'USheader']
        except Exception as e:
            current_app.logger.info("This User has been Deleted, USid is {0}, {1}".format(usid, e))
            usinfo = {"USname": "神秘的客官", "USheader": ""}
        return usinfo

    @admin_required
    def news_shelves(self):
        """资讯下架"""
        usid = request.user.id
        user = self._check_admin(usid)
        data = parameter_required(('neid',))
        neids = data.get('neid')
        current_app.logger.info("Admin {0} shelve news".format(user.ADname))
        with db.auto_commit():
            for neid in neids:
                news = News.query.filter_by_(NEid=neid, NEstatus=NewsStatus.usual.value).first_('只能下架已上架状态的资讯')
                news.NEstatus = NewsStatus.refuse.value
        return Success('下架成功', {'neid': neids})
