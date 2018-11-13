# -*- coding: utf-8 -*-
from datetime import datetime

from sqlalchemy import orm, Column as _Column, Boolean, DateTime
from sqlalchemy.ext.declarative import declarative_base, AbstractConcreteBase
from sqlalchemy import create_engine

from planet.config.http_config import HTTP_HOST
from .error_response import NotFound
from ..config import secret as cfg

DB_PARAMS = "{0}://{1}:{2}@{3}/{4}?charset={5}".format(
    cfg.sqlenginename,
    cfg.username,
    cfg.password,
    cfg.host,
    cfg.database,
    cfg.charset)
mysql_engine = create_engine(DB_PARAMS, encoding='utf-8', echo=False, pool_pre_ping=True,)
_Base = declarative_base()


class Column(_Column):
    def __init__(self, *args, **kwargs):
        self.url = kwargs.pop('url', None)
        self.url_list = kwargs.pop('url_list', None)
        super(Column, self).__init__(*args, **kwargs)


class Base(AbstractConcreteBase, _Base):
    isdelete = Column(Boolean, default=False, comment='是否删除')
    createtime = Column(DateTime, default=datetime.now, comment='创建时间')
    updatetime = Column(DateTime, default=datetime.now, onupdate=datetime.now, comment='更新时间')

    @orm.reconstructor
    def __init__(self):
        self.fields = '__all__'
        self.hide('isdelete', 'createtime', 'updatetime')

    def keys(self):
        return self.fields

    @classmethod
    def create(cls, data):
        instance = cls()
        [setattr(instance, k, v) for k, v in data.items() if v is not None]
        return instance

    def update(self, data):
        [setattr(self, k, v) for k, v in data.items() if v is not None]
        return self

    def __getitem__(self, item):
        return self.__getattr__(item)

    def __getattr__(self, item):
        cls_attr = getattr(self.__class__, item, None)
        is_url = getattr(cls_attr, 'url', None)
        is_url_list = getattr(cls_attr, 'url_list', None)
        res = getattr(self, item)
        if is_url:
            if isinstance(res, str) and not res.startswith('http'):
                res = HTTP_HOST + res
        elif is_url_list:
            res = [HTTP_HOST + r for r in res if isinstance(r, str) and not r.startswith('http')]
        return res

    def __setattr__(self, key, value):
        """
        使支持使用self.fields = '__all__'
        """
        if key == 'fields' and value == '__all__':
            self.fields = self.__table__.columns.keys()
        else:
            super(Base, self).__setattr__(key, value)

    def hide(self, *args):
        for arg in args:
            if arg in self.fields:
                self.fields.remove(arg)
        return self

    def add(self, *args):
        for arg in args:
            self.fields.append(arg)
        return self

    @property
    def clean(self):
        self.fields = []
        return self

    @property
    def all(self):
        self.fields = '__all__'
        return self

    def fill(self, name, obj, hide=None, fields=None, allow_none=True):
        """简化control层代码:
        room.fill('house', house)
        """
        if not obj and not allow_none:
            msg = u'关联的对象不存在:' + name
            raise NotFound(msg)
        if hide:
            if isinstance(obj, list):
                map(lambda x: x.hide(*hide), obj)
            else:
                if obj:
                    obj.hide(*hide)
        if fields:
            if isinstance(obj, list):
                map(lambda x: x.clean.add(*fields), obj)
            else:
                obj.fields = fields
        setattr(self, name, obj)
        return self.add(name)

