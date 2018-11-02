# -*- coding: utf-8 -*-
import os
from datetime import timedelta
from celery.schedules import crontab, crontab_parser
env = os.environ
# db
database = env.get('DXX_DB_NAME', "dxx")
host = env.get('DXX_DB_HOST', "127.0.0.1")
port = "3306"
username = env.get('DXX_DB_USER', '')
password = env.get('DXX_DB_PWD', 'password')
charset = "utf8"
sqlenginename = 'mysql+pymysql'
# 微信
appid = env.get('DXXAPPID', '')
appsecret = env.get('DXXAPPSECRET', '')
wxtoken = env.get('DXXWXTOKEN', '')
wxscope = 'snsapi_userinfo'
mch_id = env.get('MCH_ID')
mch_key = env.get('MCH_KEY')
wxpay_notify_url = env.get('DXX_PAY_REDIRECT', '')
# 支付宝
alipay_appid = env.get('ALIPAY_APPID', "2016091900546396")
app_private_path = ''
alipay_public_key_path = ''
# assert database and host and port and username and password
# assert appid and appsecret and wxscope and wxpay_notify_url


class DefaltSettig(object):
    SECRET_KEY = env.get('SECRET', 'guess')
    TOKEN_EXPIRATION = 3600 * 7 * 24  # token过期时间(秒)
    DEBUG = True
    BASEDIR = os.path.abspath(os.path.join(__file__, '../../../'))
    CELERY_TASK_SERIALIZER = 'json'
    CELERY_RESULT_SERIALIZER = 'json'
    CELERY_ACCEPT_CONTENT = ['json']
    # celery doc: http://docs.celeryproject.org/en/latest/userguide/periodic-tasks.html
    CELERY_BROKER_URL = 'redis://localhost:6379',
    CELERY_RESULT_BACKEND = 'redis://localhost:6379'
    CELERY_TIMEZONE = 'Asia/Shanghai'


class TestSetting(object):
    pass



