# -*- coding: utf-8 -*-
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
    def __init__(self, config_file_path='config.cfg'):
        self.cf = ConfigParser()
        self.config_file_path = config_file_path
        self.cf.read(self.config_file_path)

    def get_item(self, section, option):
        return self.cf.get(section, option)

    def set_item(self, section, option, value):
        self.cf.set(section, option, value.encode('utf8'))
        self.cf.write(open(self.config_file_path, "w"))