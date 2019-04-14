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
from planet.config.cfgsetting import ConfigSettings
from planet.config.enums import ItemType, NewsStatus, ApplyFrom, ApplyStatus
from planet.control.BaseControl import BASEAPPROVAL
from planet.control.CCoupon import CCoupon
from planet.extensions.register_ext import db
from planet.models import News, NewsImage, NewsVideo, NewsTag, Items, UserSearchHistory, NewsFavorite, NewsTrample, \
    Products, CouponUser, Admin, ProductBrand, User, NewsChangelog, Supplizer, Approval
from planet.models import NewsComment, NewsCommentFavorite, UserTransmit
from planet.models.trade import Coupon
from planet.service.SNews import SNews
from sqlalchemy import or_, and_
from sqlalchemy import extract
from planet.models import UserIntegral
from planet.config.enums import UserIntegralAction, UserIntegralType



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
            current_app.logger.info('Admin {0} is browsing the list of news'.format(admin.ADname))
            tourist = 'admin'
        elif is_supplizer():
            usid = request.user.id
            sup = self._check_supplizer(usid)
            current_app.logger.info('Supplizer {0} is browsing the list of news'.format(sup.SUname))
            tourist = 'supplizer'
        else:
            usid = request.user.id
            user = self.snews.get_user_by_id(usid)
            current_app.logger.info('User {0} is browsing the list of news'.format(user.USname))
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
            or_(and_(*[News.NEtitle.contains(x) for x in kw]), ),  # todo 暂更改为只匹配标题
            NewsTag.ITid == itid,
            News.NEstatus == nestatus,
            News.USid == userid
        ])
        for news in news_list:
            news.fields = ['NEid', 'NEtitle', 'NEpageviews', 'createtime']
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
                news.fill('zh_nestatus', NewsStatus(news.NEstatus).zh_value)
                news.fill('nestatus', NewsStatus(news.NEstatus).name)
                if news.NEstatus == NewsStatus.refuse.value:
                    reason = news.NErefusereason or '因内容不符合规定，审核未通过，建议修改后重新发布'
                    news.fill('refuse_info', reason)
            # 点赞数 评论数
            commentnumber = self.snews.get_news_comment_count(news.NEid)
            news.fill('commentnumber', commentnumber)
            favoritnumber = self.snews.get_news_favorite_count(news.NEid)
            news.fill('favoritnumber', favoritnumber)

            # 获取内容
            new_content = news.NEtext
            try:
                new_content = json.loads(new_content)
            except Exception as e:
                current_app.logger.error('内容转换json失败 NEid: {} ; ERROR >>> {} '.format(news.NEid, e))
                continue
            video_index, image_index, text_index = list(), list(), list()
            for index, item in enumerate(new_content):
                if item.get('type') == 'video':
                    video_index.append(index)
                elif item.get('type') == 'image':
                    image_index.append(index)
                elif item.get('type') == 'text':
                    text_index.append(index)

            if news.NEmainpic:
                showtype = 'picture'
                news.fill('mainpic', news['NEmainpic'])
            elif len(video_index):
                showtype = 'video'
                video_url = new_content[video_index[0]].get('content')['video']
                video_url = self.__verify_get_url([video_url, ])[0]
                news.fill('video', video_url)
                thumbnail_url = new_content[video_index[0]].get('content')['thumbnail']
                thumbnail_url = self.__verify_get_url([thumbnail_url, ])[0]
                news.fill('videothumbnail', thumbnail_url)
                news.fill('videoduration', new_content[video_index[0]].get('content')['duration'])
            elif len(image_index):
                showtype = 'picture'
                pic_url = new_content[image_index[0]].get('content')[0]
                pic_url = self.__verify_get_url([pic_url, ])[0]
                news.fill('mainpic', pic_url)
            else:
                showtype = 'text'
                news.fill('netext', new_content[text_index[0]].get('content')[:100] + ' ...')
            news.fill('showtype', showtype)

            # 作者信息
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
            current_app.logger.info('Admin {0} is browsing the news content'.format(admin.ADname))
            tourist = 'admin'
        elif is_supplizer():
            usid = request.user.id
            sup = self._check_supplizer(usid)
            current_app.logger.info('Supplizer {0} is browsing the news content'.format(sup.SUname))
            tourist = 'supplizer'
        else:
            usid = request.user.id
            user = self.snews.get_user_by_id(usid)
            current_app.logger.info('User {0} is browsing the news content'.format(user.USname))
            tourist = 0
        args = parameter_required(('neid',))
        neid = args.get('neid')
        news = self.snews.get_news_content({'NEid': neid})
        news.fields = ['NEid', 'NEtitle', 'NEpageviews', 'NEmainpic', 'NEisrecommend']

        if re.match(r'^[01]$', str(tourist)):  # 是普通用户或游客
            if news.NEstatus == NewsStatus.usual.value:
                self.snews.update_pageviews(news.NEid)  # 增加浏览量
            else:
                if news.USid != usid:  # 前台查看‘我发布的’ ，也需要获取非上架状态的
                    raise StatusError('该资讯正在审核中，请耐心等待')
                else:
                    pass

        # 点赞数量显示
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

        # 作者信息
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

        # 内容填充
        news_content = json.loads(news.NEtext)
        for item in news_content:
            if item.get('type') == 'video' and item['content']:
                item['content']['video'] = self.__verify_get_url([item.get('content')['video'], ])[0]
                item['content']['thumbnail'] = self.__verify_get_url([item.get('content')['thumbnail'], ])[0]
            elif item.get('type') == 'image' and item['content']:
                item['content'] = self.__verify_get_url(item['content'])
            else:
                continue
        news.fill('netext', news_content)

        # 关联标签
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
            if not news.NEmainpic:
                continue
            data = {
                'neid': news.NEid,
                'mainpic': news['NEmainpic']
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
            current_app.logger.info('User {0} created a news'.format(usname))
            nefrom = ApplyFrom.user.value
        elif admin:
            usid, usname, usheader = admin.ADid, admin.ADname, admin.ADheader
            current_app.logger.info('Admin {0} created a news'.format(usname))
            nefrom = ApplyFrom.platform.value
        elif is_supplizer():
            supplizer = Supplizer.query.filter_by_(SUid=request.user.id).first()
            usid, usname, usheader = supplizer.SUid, supplizer.SUname, supplizer.SUheader
            current_app.logger.info('Supplizer {0} created a news'.format(usname))
            nefrom = ApplyFrom.supplizer.value
        else:
            raise TokenError('用户不存在')
        data = parameter_required(('netitle', 'netext', 'items', 'source'))
        neid = str(uuid.uuid1())
        items = data.get('items')  # ['item1', 'item2']
        mainpic = data.get('nemainpic')
        coupon = data.get('coupon')  # ['coid1', 'coid2', 'coid3']
        product = data.get('product')  # ['prid1', 'prid2']
        netext = data.get('netext') or []
        coupon = json.dumps(coupon) if coupon not in self.empty and isinstance(coupon, list) else None
        product = json.dumps(product) if product not in self.empty and isinstance(product, list) else None
        isrecommend = data.get('neisrecommend', 0)
        isrecommend = True if str(isrecommend) == '1' else False

        text_list = list()
        if isinstance(netext, list):
            for text in netext:
                if text.get('type') == 'video' and text['content']:
                    text['content']['video'] = self.__verify_set_url([text.get('content')['video'], ])[0]
                    text['content']['thumbnail'] = self.__verify_set_url([text.get('content')['thumbnail'], ])[0]
                    text_list.append(text)
                elif text.get('type') == 'image' and text['content']:
                    if len(text['content']) > 9:
                        raise ParamsError('连续上传图片不允许超过9张，可在视频或文字内容后继续添加图片')
                    text['content'] = self.__verify_set_url(text['content'])
                    text_list.append(text)
                elif text.get('type') == 'text' and text['content']:
                    text_list.append(text)
                else:
                    continue

            if text_list in self.empty:
                raise ParamsError('请添加内容后发布')
            netext = json.dumps(text_list)
        else:
            raise ParamsError('netext格式错误')

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
                'NEtext': netext,
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
        super(CNews, self).create_approval('topublish', usid, neid, nefrom)
        return Success('添加成功', {'neid': neid})

    @admin_required
    def update_news(self):
        """修改资讯"""
        adid = request.user.id
        admin = Admin.query.filter_by_(ADid=adid).first_('没有该管理账号信息')
        current_app.logger.info("Admin {} has updated a news".format(admin.ADname))
        data = parameter_required(('neid',))
        neid = data.get('neid')
        items = data.get('items')  # ['item1', 'item2']
        coupon = data.get('coupon') or []  # ['coid1', 'coid2', 'coid3']
        product = data.get('product') or []  # ['prid1', 'prid2']
        netext = data.get('netext') or []
        isrecommend = data.get('neisrecommend')
        isrecommend = True if str(isrecommend) == '1' else False
        news_instance = News.query.filter_by_(NEid=neid, NEstatus=NewsStatus.refuse.value).first_('只能修改已下架状态的资讯')

        if isrecommend and not data.get('nemainpic'):
            raise ParamsError("被推荐的资讯必须上传封面图")

        coupon = json.dumps(coupon) if coupon not in self.empty and isinstance(coupon, list) else None
        product = json.dumps(product) if product not in self.empty and isinstance(product, list) else None

        text_list = list()
        if isinstance(netext, list):
            for text in netext:
                if text.get('type') == 'video' and text['content']:
                    text['content']['video'] = self.__verify_set_url([text.get('content')['video'], ])[0]
                    text['content']['thumbnail'] = self.__verify_set_url([text.get('content')['thumbnail'], ])[0]
                    text_list.append(text)
                elif text.get('type') == 'image' and text['content']:
                    if len(text['content']) > 9:
                        raise ParamsError('连续上传图片不允许超过9张，可在视频或文字内容后继续添加图片')
                    text['content'] = self.__verify_set_url(text['content'])
                    text_list.append(text)
                elif text.get('type') == 'text' and text['content']:
                    text_list.append(text)
                else:
                    continue

            if text_list in self.empty:
                raise ParamsError('请添加内容后发布')
            netext = json.dumps(text_list)
        else:
            raise ParamsError('netext格式错误')

        with db.auto_commit():
            session_list = []
            news_info = {
                'NEtitle': data.get('netitle'),
                'NEtext': netext,
                'NEstatus': NewsStatus.auditing.value,
                'COid': coupon,
                'PRid': product,
                'NEmainpic': data.get('nemainpic'),
                'NEisrecommend': isrecommend,
            }
            news_instance.update(news_info, null='no')
            session_list.append(news_instance)

            if items not in self.empty:
                item_list = list()
                for item in items:
                    item_list.append(item)
                    Items.query.filter_by_({'ITid': item, 'ITtype': ItemType.news.value}).first_('指定标签不存在')
                    exist = NewsTag.query.filter_by_(NEid=neid, ITid=item).first()
                    if not exist:
                        news_item_info = NewsTag.create({
                            'NTid': str(uuid.uuid1()),
                            'NEid': neid,
                            'ITid': item
                        })
                        session_list.append(news_item_info)
                current_app.logger.info('获取到的资讯标签为：{}'.format(item_list))
                count = NewsTag.query.filter(NewsTag.ITid.notin_(item_list), NewsTag.NEid == neid,
                                             NewsTag.isdelete == False).delete_(synchronize_session=False)
                current_app.logger.info('删除了{}个资讯标签关联'.format(count))

            # 记录修改日志
            changelog = NewsChangelog.create({
                'NCLid': str(uuid.uuid1()),
                'NEid': neid,
                'ADid': adid,
                # 'NCLoperation': operation,
            })
            session_list.append(changelog)
            db.session.add_all(session_list)
            # 添加到审批流
        super(CNews, self).create_approval('topublish', adid, neid, ApplyFrom.platform.value)
        return Success('修改成功', {'neid': neid})

    def del_news(self):
        """删除资讯"""
        if is_tourist():
            raise TokenError()
        elif is_admin():
            usid = request.user.id
            admin = self._check_admin(usid)
            current_app.logger.info('Admin {0} deleted a news'.format(admin.ADname))
        elif is_supplizer():
            usid = request.user.id
            sup = self._check_supplizer(usid)
            current_app.logger.info('Supplizer {0} deleted a news'.format(sup.SUname))
        else:
            usid = request.user.id
            user = self.snews.get_user_by_id(usid)
            current_app.logger.info('User {0} deleted a news'.format(user.USname))
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
                NewsTag.query.filter_by(NEid=neid).delete_()  # 删除标签关联
                NewsComment.query.filter_by(NEid=neid).delete_()  # 删除评论
                NewsFavorite.query.filter_by(NEid=neid).delete_()  # 删除点赞
                NewsTrample.query.filter_by(NEid=neid).delete_()  # 删除点踩
                # 如果在审核中，同时取消在进行的审批流
                try:
                    if news.NEstatus == NewsStatus.auditing.value:
                        approval_info = Approval.query.filter_by_(AVcontent=neid, AVstartid=news.USid,
                                                                  AVstatus=ApplyStatus.wait_check.value).first()
                        approval_info.update({'AVstatus': ApplyStatus.cancle.value})
                        db.session.add(approval_info)
                except Exception as e:
                    current_app.logger.error('删除圈子相关审批流时出错: {}'.format(e))
        return Success('删除成功', {'neid': neids})

    @token_required
    def news_favorite(self):
        """资讯点赞/踩"""
        usid = request.user.id
        if usid:
            user = self.snews.get_user_by_id(usid)
            current_app.logger.info('User {0} is favorite/trample news'.format(user.USname))  # 在服务器打印日志
        data = parameter_required(('neid', 'tftype'))
        neid = data.get('neid')
        news = self.snews.get_news_content({'NEid': neid})  # 获取资讯详情 判断数据库里文章是否存在
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

                    # 点赞加星币，一天最多加五次，一次加三个
                    now_time = datetime.now()
                    count = s.query(NewsFavorite).filter(
                        extract('month', NewsFavorite.createtime) == now_time.month,
                        extract('year', NewsFavorite.createtime) == now_time.year,
                        extract('day', NewsFavorite.createtime) == now_time.day,
                        NewsFavorite.USid == usid).count()
                    if count <= 5:
                        integral = ConfigSettings().get_item('integralbase', 'integral_favorite')
                        # integral = '3'  # 引用签到配置文件
                        ui = UserIntegral.create({
                            'UIid': str(uuid.uuid1()),
                            'USid': usid,
                            'UIintegral': integral,
                            'UIaction': UserIntegralAction.favorite.value,
                            'UItype': UserIntegralType.income.value
                        })
                        s.add(ui)
                        user.update({'USintegral': user.USintegral + int(ui.UIintegral)})
                        s.add(user)
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
                current_app.logger.info('User {0} is checking the news commentary'.format(user.USname))
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
    def create_comment(self):  # 进行评论
        usid = request.user.id
        user = self.snews.get_user_by_id(usid)
        usname, usheader = user.USname, user.USheader
        current_app.logger.info('User {0}  created a news commentary'.format(user.USname))
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
                # 评论加星币，一天最多加五次，一次加三个
                now_time = datetime.now()
                count = nc.query(NewsComment).filter(
                    extract('month', NewsComment.createtime) == now_time.month,
                    extract('year', NewsComment.createtime) == now_time.year,
                    extract('day', NewsComment.createtime) == now_time.day,
                    NewsComment.USid == usid).count()
                if count <= 5:
                    # integral = '3'
                    integral = ConfigSettings().get_item('integralbase', 'integral_commit')
                    ui = UserIntegral.create({
                        'UIid': str(uuid.uuid1()),
                        'USid': usid,
                        'UIintegral': integral,
                        'UIaction': UserIntegralAction.commit.value,
                        'UItype': UserIntegralType.income.value
                    })
                    nc.add(ui)
                    user.update({'USintegral': user.USintegral + int(ui.UIintegral)})
                    nc.add(user)
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
                # 回复评论加星币，一天最多加五次，一次加三个
                now_time = datetime.now()
                count = r.query(NewsComment).filter(
                    extract('month', NewsComment.createtime) == now_time.month,
                    extract('year', NewsComment.createtime) == now_time.year,
                    extract('day', NewsComment.createtime) == now_time.day,
                    NewsComment.USid == usid).count()
                if count <= 5:
                    # integral = '3'
                    integral = ConfigSettings().get_item('integralbase', 'integral_commit')
                    ui = UserIntegral.create({
                        'UIid': str(uuid.uuid1()),
                        'USid': usid,
                        'UIintegral': integral,
                        'UIaction': UserIntegralAction.commit.value,
                        'UItype': UserIntegralType.income.value
                    })
                    r.add(ui)
                    user.update({'USintegral': user.USintegral + int(ui.UIintegral)})
                    r.add(user)
            # 评论后返回刷新结果
            news_comment = NewsComment.query.filter_by_(NCid=ncrootid).first()
            self._get_one_comment(news_comment, neid, usid)
        return Success('评论成功', data=news_comment)

    @token_required
    def comment_favorite(self):
        """评论点赞"""
        usid = request.user.id
        user = self.snews.get_user_by_id(usid)
        current_app.logger.info('User {0}, comment favorite'.format(user.USname))
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
    def transmit_content(self):
        """转发"""
        usid = request.user.id
        if usid:
            user = self.snews.get_user_by_id(usid)
            current_app.logger.info('User {0} transmit '.format(user.USname))  # 在服务器打印日志
        data = parameter_required(('Contentid', 'UTtype'))
        contentid = data.get('Contentid')
        uttype = data.get('Uttype')  # {1:资讯，2：商品，3：活动}
        with self.snews.auto_commit() as s:
            content_transmit = UserTransmit.create({
                'UTid': str(uuid.uuid1()),
                'Contentid': contentid,
                'USid': usid,
                'UTtype': uttype
            })
            s.add(content_transmit)
            now_time = datetime.now()
            count = s.query(UserTransmit).filter(
                extract('month', UserTransmit.createtime) == now_time.month,
                extract('year', UserTransmit.createtime) == now_time.year,
                extract('day', UserTransmit.createtime) == now_time.day,
                UserTransmit.USid == usid).count()
            if count <= 5:
                integral = '5'
                # integral = ConfigSettings().get_item('integralbase', 'integral_transmit')
                ui = UserIntegral.create({
                    'UIid': str(uuid.uuid1()),
                    'USid': usid,
                    'UIintegral': integral,
                    'UIaction': UserIntegralAction.transmit.value,
                    'UItype': UserIntegralType.income.value
                })
                s.add(ui)
                user.update({'USintegral': user.USintegral + int(ui.UIintegral)})
                s.add(user)

    @token_required
    def del_comment(self):
        """删除评论"""
        usid = request.user.id
        user = self.snews.get_user_by_id(usid)
        current_app.logger.info('User {0} deleted a news commentary'.format(user.USname))
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
            current_app.logger.info("This error is not real, User has been Deleted, USid is {0}, {1}".format(usid, e))
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

    def convert_test(self):
        """仅测试用，转换原圈子格式数据的"""
        with db.auto_commit():
            all_news = News.query.filter_by_().all()
            for news in all_news:
                json_list = list()
                old_text = news.NEtext
                images = NewsImage.query.filter_by_(NEid=news.NEid).order_by(NewsImage.NIsort.asc()).all()
                if images:
                    img_list = list()
                    for img in images:
                        img_list.append(img.NIimage)
                    img_dict = {'type': 'image', 'content': img_list}
                    json_list.append(img_dict)
                video = NewsVideo.query.filter_by_(NEid=news.NEid).first()
                if video:
                    json_list.append({'type': 'video', 'content': {'video': video.NVvideo, 'thumbnail': video.NVthumbnail,
                                                                   'duration': video.NVduration}})
                json_list.append({'type': 'text', 'content': old_text})

                json_list = json.dumps(json_list)
                news.update({'NEtext': json_list})
                db.session.add(news)

    def __verify_set_url(self, url_list):
        from planet.config.http_config import MEDIA_HOST
        res = list()
        for url in url_list:
            if isinstance(url, str) and url.startswith(MEDIA_HOST):
                res.append(url[len(MEDIA_HOST):])
            else:
                res.append(url)
        return res

    def __verify_get_url(self, url_list):
        from planet.config.http_config import MEDIA_HOST
        res = list()
        for url in url_list:
            if isinstance(url, str) and not url.startswith('http'):
                rs = MEDIA_HOST + url
                res.append(rs)
            else:
                res.append(url)
        return res


# if __name__ == '__main__':
#     from planet import create_app
#     app = create_app()
#     with app.app_context():
#         CNews().convert_test()
