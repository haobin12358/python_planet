# -*- coding: utf-8 -*-
import json
from datetime import datetime

from sqlalchemy import orm, Column as _Column, Boolean, DateTime
from sqlalchemy.ext.declarative import declarative_base, AbstractConcreteBase
from sqlalchemy import create_engine

from planet.config.http_config import MEDIA_HOST
from planet.extensions.register_ext import db
from .error_response import NotFound
from ..config.secret import DB_PARAMS
mysql_engine = create_engine(DB_PARAMS, encoding='utf-8', echo=False, pool_pre_ping=True,)
_Base = declarative_base()


class Column(_Column):
    def __init__(self, *args, **kwargs):
        self.url = kwargs.pop('url', None)
        self.url_list = kwargs.pop('url_list', None)
        super(Column, self).__init__(*args, **kwargs)


class Base(db.Model):
    __abstract__ = True
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
        return instance._set_attrs(data)

    def update(self, data, null='ignore'):
        return self._set_attrs(data, null=null)

    def __getitem__(self, item):
        cls_attr = getattr(self.__class__, item, None)
        is_url = getattr(cls_attr, 'url', None)
        is_url_list = getattr(cls_attr, 'url_list', None)
        res = getattr(self, item)
        if is_url:
            if isinstance(res, str) and not res.startswith('http'):
                res = MEDIA_HOST + res
        elif is_url_list:
            if res:
                res = json.loads(res)
                rs = []
                for r in res:
                    rs.append(MEDIA_HOST + r if isinstance(r, str) and not r.startswith('http') else r)
                res = rs
            else:
                res = []
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

    def _set_attrs(self, data, null='ignore'):
        for k, v in data.items():
            if v is None and null == 'ignore':
                continue
            cls_attr = getattr(self.__class__, k)
            is_url_list = getattr(cls_attr, 'url_list', None)
            is_url = getattr(cls_attr, 'url', None)
            if is_url:
                if isinstance(v, str) and v.startswith(MEDIA_HOST):  # 如果链接中有httphost, 则需要去掉
                    setattr(self, k, v[len(MEDIA_HOST):])
                else:
                    setattr(self, k, v)
            elif isinstance(v, list) and is_url_list:
                v_items = []
                for v_item in v:
                    if isinstance(v, str) and v.startswith(MEDIA_HOST):
                        v_items.append(v_item[len(MEDIA_HOST):])
                    else:
                        v_items.append(v_item)
                setattr(self, k, json.dumps(v_items))
            else:
                setattr(self, k, v)
        return self
