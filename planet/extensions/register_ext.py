# -*- coding: utf-8 -*-
import os
from contextlib import contextmanager

import redis
from alipay import AliPay
from flask_caching import Cache
from flask_sqlalchemy import SQLAlchemy as _SQLAlchemy

from planet.common.query_session import Query
from planet.config.secret import DB_PARAMS, alipay_appid, alipay_notify, app_private_path, alipay_public_key_path, \
    appid, mch_id, mch_key, wxpay_notify_url, BASEDIR, server_dir, cache_redis, apiclient_key, apiclient_cert
from planet.extensions.weixin import WeixinPay
from .loggers import LoggerHandler
from .weixin.mp import WeixinMP
from planet.config.secret import SERVICE_APPID, SERVICE_APPSECRET, SUBSCRIBE_APPID, SUBSCRIBE_APPSECRET


class SQLAlchemy(_SQLAlchemy):
    def init_app(self, app):
        app.config.setdefault('SQLALCHEMY_DATABASE_URI', DB_PARAMS)
        app.config.setdefault('SQLALCHEMY_TRACK_MODIFICATIONS', False)
        # app.config.setdefault('SQLALCHEMY_ECHO', True)  # 开启sql日志
        super(SQLAlchemy, self).init_app(app)

    @contextmanager
    def auto_commit(self):
        try:
            yield
            self.session.commit()
        except Exception as e:
            db.session.rollback()
            raise e


alipay = AliPay(
    appid=alipay_appid,
    app_notify_url=alipay_notify,  # 默认回调url
    app_private_key_string=open(app_private_path).read(),
    alipay_public_key_string=open(alipay_public_key_path).read(),
    debug=True
    # sign_type="RSA2",  # RSA 或者 RSA2
     )
wx_pay = WeixinPay(appid, mch_id, mch_key, wxpay_notify_url, apiclient_key, apiclient_cert)
db = SQLAlchemy(query_class=Query, session_options={"expire_on_commit": False, "autoflush": False})

mp_server = WeixinMP(SERVICE_APPID, SERVICE_APPSECRET,
                     ac_path=os.path.join(server_dir, ".access_token"),
                     jt_path=os.path.join(server_dir, ".jsapi_ticket"))

mp_subscribe = WeixinMP(SUBSCRIBE_APPID, SUBSCRIBE_APPSECRET,
                     ac_path=os.path.join(server_dir, ".access_token"),
                     jt_path=os.path.join(server_dir, ".jsapi_ticket"))


conn = redis.Redis(host='localhost', port=6379, db=1)
cache = Cache(config=cache_redis)


def register_ext(app):
    db.init_app(app)
    cache.init_app(app)
    LoggerHandler(app, file='/tmp/planet/').error_handler()
    from planet.extensions.tasks import celery
    celery.init_app(app)
