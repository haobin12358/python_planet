# -*- coding: utf-8 -*-
import os
from datetime import timedelta

from celery.schedules import crontab

from planet.config.http_config import API_HOST

env = os.environ
BASEDIR = os.path.abspath(os.path.join(__file__, '../../../'))
# db
database = env.get('DXX_DB_NAME', "dxx")
host = env.get('DXX_DB_HOST', "127.0.0.1")
port = "3306"
username = env.get('DXX_DB_USER', '')
password = env.get('DXX_DB_PWD', 'password')
charset = "utf8mb4"
sqlenginename = 'mysql+pymysql'
DB_PARAMS = "{0}://{1}:{2}@{3}/{4}?charset={5}".format(
    sqlenginename,
    username,
    password,
    host,
    database,
    charset)
# 微信
appid = env.get('DXXAPPID', 'wxe8e8f6b9351d3587')
appsecret = env.get('DXXAPPSECRET', 'b89e22f046d33b39c7a4afa485e661dc')
wxtoken = env.get('DXXWXTOKEN', '')
wxscope = 'snsapi_userinfo'
mch_id = env.get('MCH_ID')
mch_key = env.get('MCH_KEY')
wxpay_notify_url = API_HOST + '/api/v1/order/wechat_notify'
apiclient_cert = os.path.join(BASEDIR, 'pem', 'apiclient_cert.pem')
apiclient_key = os.path.join(BASEDIR, 'pem', 'apiclient_key.pem')
# 支付宝
alipay_appid = "2018111962237528"
app_private_path = os.path.join(BASEDIR, 'pem', 'app_private_key.pem')
alipay_public_key_path = os.path.join(BASEDIR, 'pem', 'alipay_pub.pem')  # pub是大猩猩的
alipay_notify = API_HOST + '/api/v1/order/alipay_notify'
# 阿里云短信
# ACCESS_KEY_ID/ACCESS_KEY_SECRET 根据实际申请的账号信息进行替换
ACCESS_KEY_ID = env.get('ACCESS_KEY_ID')
ACCESS_KEY_SECRET = env.get('ACCESS_KEY_SECRET')
# 数字签名
SignName = env.get("SignName", "etech研发团队")
# 短信模板
TemplateCode = env.get("TemplateCode")
# 身份实名认证
ID_CHECK_APPCODE = env.get("ID_CHECK_APPCODE")

# 快递物流查询
kd_api_code = env.get('KDApiKey', 'guess')
kd_api_url = 'https://kdwlcxf.market.alicloudapi.com/kdwlcx'

# 微信公众号的配置
SERVICE_APPID = env.get('DXXSERVICE_APPID', 'wxe8e8f6b9351d3587')
SERVICE_APPSECRET = env.get('DXXSERVICE_APPSECRET', 'b89e22f046d33b39c7a4afa485e661dc')

SUBSCRIBE_APPID = env.get('DXXSERVICE_APPID', 'wxe8e8f6b9351d3587')
SUBSCRIBE_APPSECRET = env.get('DXXSERVICE_APPSECRET', 'b89e22f046d33b39c7a4afa485e661dc')
server_dir = os.path.join(BASEDIR, 'wxservice')
subscribe_dir = os.path.join(BASEDIR, 'wxsubscribe_dir')
if not os.path.isdir(server_dir):
    os.makedirs(server_dir)

if not os.path.isdir(subscribe_dir):
    os.makedirs(subscribe_dir)
# cache
cache_redis = {"CACHE_TYPE": "redis",
              "CACHE_REDIS_HOST": "localhost",
              "CACHE_REDIS_PORT": 6379,
              "CACHE_REDIS_DB": 1}


class DefaltSettig(object):
    SECRET_KEY = env.get('SECRET', 'guess')
    TOKEN_EXPIRATION = 3600 * 7 * 24  # token过期时间(秒)
    DEBUG = True
    BASEDIR = BASEDIR
    CELERY_TASK_SERIALIZER = 'json'
    CELERY_RESULT_SERIALIZER = 'json'
    CELERY_ACCEPT_CONTENT = ['json']
    # celery doc: http://docs.celeryproject.org/en/latest/userguide/periodic-tasks.html
    CELERY_BROKER_URL = 'redis://localhost:6379',
    CELERY_RESULT_BACKEND = 'redis://localhost:6379'
    CACHE_REDIS_URL = 'redis://localhost:6379/1'
    CELERY_TIMEZONE = 'Asia/Shanghai'
    CELERYBEAT_SCHEDULE = {
        'fetch_share_deal': {
            'task': 'fetch_share_deal',
            # 'schedule': crontab(hour=0, minute=1)
            'schedule': timedelta(hours=6)
        },
        'auto_evaluate': {
            'task': 'auto_evaluate',
            'schedule': crontab(hour=4, minute=30, day_of_week=[0, 1, 2, 3, 4, 5, 6])
        }
    }


class TestSetting(object):
    pass
