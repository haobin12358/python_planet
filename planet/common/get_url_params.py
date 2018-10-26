# *- coding:utf8 *-
import sys
import os
import urlparse
import urllib
sys.path.append(os.path.dirname(os.getcwd()))


class GetUrlParams(object):

    @staticmethod
    def url_params_to_dict(url):
        """
        url 里不能有# 或者 ; 否则无法正常读取参数，可以把url split("#") 取[-1] 来取值
        :param url:
        :return:
        """
        query = urlparse.urlparse(url).query
        return dict([(k, v[0]) for k, v in urlparse.parse_qs(query).items()])

    @staticmethod
    def dict_to_url_params(paramsdict):
        """
        转置为不带? 的str，需要自行拼接? ETC:
        {'openid': 'oV6d90u8IIdfOi2bMBopWxSSLwH0',
        'prid': '04c03150-1ca3-4dfb-b8fa-6d4296107b28'} ==>

        openid=oV6d90u8IIdfOi2bMBopWxSSLwH0&prid=04c03150-1ca3-4dfb-b8fa-6d4296107b28
        :param paramsdict:
        :return:
        """
        return urllib.urlencode(paramsdict, doseq=True)