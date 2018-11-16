# -*- coding: utf-8 -*-
from flask_caching import Cache
from flask_sqlalchemy import SQLAlchemy as _SQLAlchemy

from planet.common.query_session import Query
from planet.config.secret import DB_PARAMS
from .loggers import LoggerHandler


class SQLAlchemy(_SQLAlchemy):
    def init_app(self, app):
        app.config.setdefault('SQLALCHEMY_DATABASE_URI', DB_PARAMS)
        app.config.setdefault('SQLALCHEMY_TRACK_MODIFICATIONS', False)
        # app.config.setdefault('SQLALCHEMY_ECHO', True)  # 开启sql日志
        super(SQLAlchemy, self).init_app(app)


cache = Cache()
db = SQLAlchemy(query_class=Query)


def register_ext(app):
    db.init_app(app)
    cache.init_app(app, config={'CACHE_TYPE': 'simple'})
    LoggerHandler(app, file='/tmp/planet/').error_handler()
