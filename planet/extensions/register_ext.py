# -*- coding: utf-8 -*-
from flask_caching import Cache

from .loggers import LoggerHandler

cache = Cache()


def register_ext(app):
    cache.init_app(app, config={'CACHE_TYPE': 'simple'})
    LoggerHandler(app, file='/tmp/planet/').error_handler()
