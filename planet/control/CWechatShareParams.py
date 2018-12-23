# -*- coding: utf-8 -*-
from planet.common.params_validates import parameter_required
from planet.common.success_response import Success
from planet.config.cfgsetting import ConfigSettings


class CWechatShareParams(object):

    # @admin_required
    def set_share_params(self):
        """设置微信分享参数"""
        # usid = request.user.id
        # admin = Admin.query.filter_by_(ADid=usid).first_('非管理员权限')
        # current_app.logger.info("ADMIN {} is setting share params args".format(admin.ADname))
        data = parameter_required(('title', 'content', 'img'))
        title = data.get('title')
        content = data.get('content')
        img = data.get('img')
        cfs = ConfigSettings()
        cfs.set_item('wxshareparams', 'title', title)
        cfs.set_item('wxshareparams', 'content', content)
        cfs.set_item('wxshareparams', 'img', img)
        return Success('设置成功', data={'title': title, 'content': content, 'img': img})

    def get_share_params(self):
        """获取微信分享参数"""
        args = parameter_required()
        # todo 具体分享商品/资讯/活动 时展示的图片不同

        cfs = ConfigSettings()
        title = cfs.get_item('wxshareparams', 'title')
        content = cfs.get_item('wxshareparams', 'content')
        img = cfs.get_item('wxshareparams', 'img')
        data = {'title': title,
                'content': content,
                'img': img
                }
        return Success(data=data)
