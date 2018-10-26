# *- coding:utf8 *-
import sys
import os
import configparser
sys.path.append(os.path.dirname(os.getcwd()))


class Partner(object):
    """佣金分成设置, 后续设置"""
    def __init__(self, config_file_path='WeiDian/config/divide_config.cfg'):
        self.cf = configparser.ConfigParser()
        self.config_file_path = config_file_path
        self.cf.read(self.config_file_path)

    @property
    def one_level_divide(self):
        return float(self.cf.get('divide', 'one_level'))

    @one_level_divide.setter
    def one_level_divide(self, raw):
        self.cf.set('divide', 'one_level', raw)
        self.cf.write(open(self.config_file_path, "w"))

    @property
    def two_level_divide(self):
        return float(self.cf.get('divide', 'two_level'))

    @two_level_divide.setter
    def two_level_divide(self, raw):
        self.cf.set('divide', 'two_level', raw)
        self.cf.write(open(self.config_file_path, "w"))

    @property
    def three_level_divide(self):
        return float(self.cf.get('divide', 'three_level'))

    @three_level_divide.setter
    def three_level_divide(self, raw):
        self.cf.set('divide', 'three_level', raw)
        self.cf.write(open(self.config_file_path, "w"))

    @property
    def access_token(self):
        return [
            self.cf.get("access_token", "access_token"),
            self.cf.get("access_token", "jsapiticket"),
            self.cf.get("access_token", "lasttime")]

    @access_token.setter
    def access_token(self, args):
        token, jsapiticket, updatetime = args[0], args[1], args[2]
        self.cf.set('access_token', 'access_token', token)
        self.cf.set("access_token", "lasttime", updatetime)
        self.cf.set("access_token", "jsapiticket", jsapiticket)
        self.cf.write(open(self.config_file_path, "w"))

    def get_item(self, section, option):
        value = self.cf.get(section, option)
        return value

    def set_item(self, section, option, value):
        self.cf.set(section, option, value)
        self.cf.write(open(self.config_file_path, "w"))
        return 'ok'


if __name__ == '__main__':
    pass