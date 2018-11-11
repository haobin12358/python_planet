# -*- coding: utf-8 -*-
import logging
import os
import sys
from logging.handlers import TimedRotatingFileHandler


class LoggerHandler():
    def __init__(self, app=None, file='', format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"):
        self.file = file
        self.set_format(format)
        if app is not None:
            self.init_app(app)
            self.app = app

    def init_app(self, app):
        logger_dir = self.file
        if not os.path.isdir(logger_dir):
            os.makedirs(logger_dir)
        formatter = logging.Formatter(self.format)
        log_file_handler = TimedRotatingFileHandler(filename=os.path.join(logger_dir, 'log'), when="d")
        log_file_handler.setFormatter(formatter)
        log_file_handler.setLevel(logging.DEBUG)
        app.logger.addHandler(log_file_handler)
        app.logger.info('>>>>>>>>>>>>>>>>>>{}<<<<<<<<<<<<<<<<<<<'.format('start success'))

        # stream_handler = logging.StreamHandler(sys.stdout)
        # stream_handler.setFormatter(formatter)
        # app.logger.addHandler(stream_handler)

    def set_format(self, format):
        self.format = format


