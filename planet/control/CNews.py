# -*- coding: utf-8 -*-
import re
import uuid
from datetime import datetime

from flask import request
from planet.common.error_response import TokenError, ParamsError, SystemError, NotFound
from planet.common.params_validates import parameter_required
from planet.common.request_handler import gennerc_log
from planet.common.success_response import Success
from planet.common.token_handler import token_required, is_tourist
from planet.config.enums import ItemType, NewsStatus
from planet.models import News, NewsImage, NewsVideo, NewsTag, Items, UserSearchHistory, NewsFavorite, NewsTrample
from planet.models import NewsComment, NewsCommentFavorite
from planet.service.SNews import SNews
from sqlalchemy import or_, and_


class CNews(object):
    def __init__(self):
        self.snews = SNews()
        self.empty = ['', {}, [], [''], None]

    def get_all_news(self):
        if not is_tourist():
            usid = request.user.id
            user = self.snews.get_user_by_id(usid)
            gennerc_log('get user is {0}'.format(user.USname))
            if not user:
                raise TokenError('token error')
            tourist = 0
        else:
            usid = None
            tourist = 1
        args = parameter_required(('page_num', 'page_size'))
        itid = args.get('itid')
        kw = args.get('kw', '').split() or ['']  # 关键词
        nestatus = args.get('nestatus') or 'usual'
        nestatus = getattr(NewsStatus, nestatus).value
        userid = None
        if str(itid) == 'mynews':
            userid = usid
            itid = None
            nestatus = None
        news_list = self.snews.get_news_list([
            or_(and_(*[News.NEtitle.contains(x) for x in kw]), and_(*[News.NEtext.contains(x) for x in kw])),
            NewsTag.ITid == itid,
            News.NEstatus == nestatus,
            News.USid == userid
        ])
        for news in news_list:
            news.fields = ['NEid', 'NEtitle', 'NEpageviews']
            self.snews.update_pageviews(news.NEid)
            if usid:
                is_favorite = self.snews.news_is_favorite(news.NEid, usid)
                favorite = 1 if is_favorite else 0
            else:
                favorite = 0
            news.fill('is_favorite', favorite)
            if userid:
                news_status = news.NEstatus
                news.fill('nestatus', NewsStatus(news_status).name)
                if str(news_status) == '0':
                    news.fill('refuse_info', '因内容不符合规定，审核未通过，建议修改后重新发布')
                    # todo 获取审批拒绝理由
            commentnumber = self.snews.get_news_comment_count(news.NEid)
            news.fill('commentnumber', commentnumber)
            favoritnumber = self.snews.get_news_favorite_count(news.NEid)
            news.fill('favoritnumber', favoritnumber)
            video = self.snews.get_news_video(news.NEid)
            if video:
                video_source = video['NVvideo']
                showtype = 'video'
                video_thumbnail = video['NVthumbnail']
                dur_time = video['NVduration']
                news.fill('video', video_source)
                news.fill('videothumbnail', video_thumbnail)
                news.fill('videoduration', dur_time)
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
        if not is_tourist():
            usid = request.user.id
            if usid:
                user = self.snews.get_user_by_id(usid)
                gennerc_log('get user is {0}'.format(user.USname))
                if not user:
                    raise TokenError('token error')
                tourist = 0
        else:
            usid = None
            tourist = 1
        args = parameter_required(('neid',))
        news = self.snews.get_news_content({'NEid': args.get('neid')})
        news.fields = ['NEtitle', 'NEpageviews']
        self.snews.update_pageviews(news.NEid)
        if usid:
            is_favorite = self.snews.news_is_favorite(news.NEid, usid)
            favorite = 1 if is_favorite else 0
            is_trample = self.snews.news_is_trample(news.NEid, usid)
            trample = 1 if is_trample else 0
        else:
            favorite = 0
            trample = 0
        news.fill('is_favorite', favorite)
        news.fill('is_trample', trample)
        commentnumber = self.snews.get_news_comment_count(news.NEid)
        news.fill('commentnumber', commentnumber)
        favoritnumber = self.snews.get_news_favorite_count(news.NEid)
        news.fill('favoritnumber', favoritnumber)
        tramplenumber = self.snews.get_news_trample_count(news.NEid)
        news.fill('tramplenumber', tramplenumber)
        image_list = self.snews.get_news_images(news.NEid)
        if image_list:
            [image.hide('NEid') for image in image_list]
        news.fill('image', image_list)
        video = self.snews.get_news_video(news.NEid)
        if video:
            video.hide('NEid')
            news.fill('video', video)
        tags = self.snews.get_item_list((NewsTag.NEid == news.NEid,))
        if tags:
            [tag.hide('PSid') for tag in tags]
        news.fill('items', tags)
        netext = news.NEtext
        news.fill('netext', netext)
        return Success(data=news).get_body(istourist=tourist)

    @token_required
    def create_news(self):
        """创建资讯"""
        usid = request.user.id
        if usid:
            user = self.snews.get_user_by_id(usid)
            gennerc_log('get user is {0}'.format(user.USname))
            if not user:
                raise TokenError('token error')
        data = parameter_required(('netitle', 'netext', 'items', 'source'))
        neid = str(uuid.uuid1())
        images = data.get('images')  # [{niimg:'url', nisort:1},]
        items = data.get('items')  # ['item1', 'item2',]
        video = data.get('video')  # {nvurl:'url', nvthum:'url'}
        with self.snews.auto_commit() as s:
            session_list = []
            news_info = News.create({
                'NEid': neid,
                'USid': request.user.id,
                'NEtitle': data.get('netitle'),
                'NEtext': data.get('netext'),
                'NEstatus': NewsStatus.auditing.value
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
        return Success('添加成功', {'neid': neid})

    @token_required
    def news_favorite(self):
        """资讯点赞/踩"""
        usid = request.user.id
        if usid:
            user = self.snews.get_user_by_id(usid)
            gennerc_log('get user is {0}'.format(user.USname))
        data = parameter_required(('neid', 'tftype'))
        neid = data.get('neid')
        news = self.snews.get_news_content({'NEid': neid})
        tftype = data.get('tftype')  # {1:点赞, 0:点踩}
        if not re.match(r'^[0|1]$', str(tftype)):
            raise ParamsError('tftype, 参数异常')
        msg = '取消成功'
        if str(tftype) == '1':
            is_favorite = self.snews.news_is_favorite(neid, usid)
            if not is_favorite:
                with self.snews.auto_commit() as s:
                    news_favorite = NewsFavorite.create({
                        'NEFid': str(uuid.uuid1()),
                        'NEid': neid,
                        'USid': usid
                    })
                    s.add(news_favorite)
                msg = '点赞成功'
            else:
                cancel_favorite = self.snews.cancel_favorite(neid, usid)
                if not cancel_favorite:
                    raise SystemError('服务器繁忙')
        else:
            is_trample = self.snews.news_is_trample(news.NEid, usid)
            if not is_trample:
                with self.snews.auto_commit() as sn:
                    news_trample = NewsTrample.create({
                        'NETid': str(uuid.uuid1()),
                        'NEid': neid,
                        'USid': usid
                    })
                    sn.add(news_trample)
                msg = '踩了一下'
            else:
                cancel_trample = self.snews.cancel_trample(neid, usid)
                if not cancel_trample:
                    raise SystemError('服务器繁忙')
        favorite = self.snews.news_is_favorite(neid, usid)
        favorite = 1 if favorite else 0
        trample = self.snews.news_is_trample(news.NEid, usid)
        trample = 1 if trample else 0
        return Success(message=msg, data={'neid': neid, 'is_favorite': favorite, 'is_trample': trample})

    def get_news_comment(self):
        """获取资讯评论"""
        if not is_tourist():
            usid = request.user.id
            if usid:
                user = self.snews.get_user_by_id(usid)
                gennerc_log('get user is {0}'.format(user.USname))
                if not user:
                    raise TokenError('token error')
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
            reply_comments = NewsComment.query.filter(NewsComment.NEid == neid,
                                                      NewsComment.isdelete == False,
                                                      NewsComment.NCrootid == news_comment.NCid
                                                      ).order_by(NewsComment.createtime.desc()).all()
            for reply_comment in reply_comments:
                re_user = self.fill_user_info(reply_comment.USid)
                reply_comment.fill('commentuser', re_user['USname'])
                replied_user = self.snews.get_comment_reply_user((NewsComment.NCid == reply_comment.NCparentid,))
                repliedusername = replied_user.USname if replied_user else '匿名用户'
                if repliedusername == re_user['USname']:
                    repliedusername = ''
                reply_comment.fill('replieduser', repliedusername)
            news_comment.fill('reply', reply_comments)
            user_info = self.fill_user_info(news_comment.USid)
            news_comment.fill('user', user_info)
            if usid:
                is_favorite = self.snews.comment_is_favorite(news_comment.NCid, usid)
                favorite = 1 if is_favorite else 0
            else:
                favorite = 0
            news_comment.fill('is_favorite', favorite)
            createtime = news_comment.createtime or datetime.now()
            createtime = str(createtime).replace('-', '/')[:19]
            news_comment.fill('createtime', createtime)
        return Success(data=news_comments).get_body(comment_count=comment_total_count, istourist=tourist)

    # todo 删除源评论时候需要同时删除源评论下所有回复

    @token_required
    def create_comment(self):
        usid = request.user.id
        user = self.snews.get_user_by_id(usid)
        gennerc_log('get user is {0}'.format(user.USname))
        if not user:
            raise TokenError('token error')
        data = parameter_required(('neid', 'nctext'))
        neid = data.get('neid')
        self.snews.get_news_content({'NEid': neid, 'isdelete': False})
        ncid = data.get('ncid')
        comment_ncid = str(uuid.uuid1())
        reply_ncid = str(uuid.uuid1())
        if ncid in self.empty:
            with self.snews.auto_commit() as nc:
                comment = NewsComment.create({
                    'NCid': comment_ncid,
                    'NEid': neid,
                    'USid': usid,
                    'NCtext': data.get('nctext'),
                })
                nc.add(comment)
            re_data = comment_ncid
        else:
            news_comment = NewsComment.query.filter(NewsComment.NCid == ncid, NewsComment.isdelete == False).first()
            if not news_comment:
                raise NotFound('该评论已删除')
            ncrootid = news_comment.NCrootid
            if not ncrootid:
                ncrootid = ncid
            with self.snews.auto_commit() as r:
                reply = NewsComment.create({
                    'NCid': reply_ncid,
                    'NEid': neid,
                    'USid': usid,
                    'NCtext': data.get('nctext'),
                    'NCparentid': ncid,
                    'NCrootid': ncrootid,
                })
                r.add(reply)
            re_data = reply_ncid
        return Success('评论成功', data={'ncid': re_data})

    @token_required
    def comment_favorite(self):
        """评论点赞"""
        usid = request.user.id
        user = self.snews.get_user_by_id(usid)
        gennerc_log('get user is {0}'.format(user.USname))
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
        # todo 删除评论
        pass

    def fill_user_info(self, usid):
        try:
            usinfo = self.snews.get_user_by_id(usid)
        except Exception as f:
            gennerc_log("this user is deleted, error is {}".format(f))
            user_dict = {"USname": "匿名用户", "USheader": ""}
            return user_dict
        usinfo.fields = ['USname', 'USheader']
        return usinfo
