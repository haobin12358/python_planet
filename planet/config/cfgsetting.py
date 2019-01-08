# -*- coding: utf-8 -*-
from flask import current_app

try:
    import ConfigParser
except Exception as e:
    from configparser import ConfigParser


def singleton(cls, *args, **kw):
    """ singleton decorator """
    instances = {}

    def _singleton(*args):
        if cls not in instances:
            instances[cls] = cls(*args, **kw)
        return instances[cls]
    return _singleton


class ConfigSettings(object):
    """读取和写入配置文件"""
    def __init__(self, config_file_path='planet/config/planet.cfg'):
        self.cf = ConfigParser()
        self.config_file_path = config_file_path
        self.cf.read(self.config_file_path)

    def get_item(self, section, option):
        print(type(self.cf.get(section, option)))
        return self.cf.get(section, option)

    def set_item(self, section, option, value):
        self.cf.set(section, option, value)
        # self.cf.write(open(self.config_file_path, "w"))
        self.write_file()

    def write_file(self):
        with open(self.config_file_path, "w") as cfg:
            self.cf.write(cfg)
            current_app.logger.info('file is closed')
