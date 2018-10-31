# -*- coding: utf-8 -*-
from datetime import datetime

from sqlalchemy import orm, Column, Boolean, DateTime
from sqlalchemy.ext.declarative import declarative_base, AbstractConcreteBase
from sqlalchemy import create_engine

from .error_response import NotFound
from ..config import secret as cfg

DB_PARAMS = "{0}://{1}:{2}@{3}/{4}?charset={5}".format(
    cfg.sqlenginename,
    cfg.username,
    cfg.password,
    cfg.host,
    cfg.database,
    cfg.charset)
mysql_engine = create_engine(DB_PARAMS, encoding='utf-8', echo=False, pool_pre_ping=True)
_Base = declarative_base()


class Base(AbstractConcreteBase, _Base):
    isdelete = Column(Boolean, default=False, comment='是否删除')
    createtime = Column(DateTime, default=datetime.now, comment='创建时间')
    updatetime = Column(DateTime, default=datetime.now, comment='更新时间')

    @orm.reconstructor
    def __init__(self):
        self.fields = '__all__'
        self.hide('isdelete')

    def keys(self):
        return self.fields

    @classmethod
    def create(cls, data):
        instance = cls()
        for k, v in data.items():
            setattr(instance, k, v)
        return instance

    def __getitem__(self, item):
        return getattr(self, item)

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
            room.fill(self.sroom.get_house_by_hoid(room.HOid), 'house')
            等同于:
            room.house = self.sroom.get_house_by_hoid(room.HOid)
            room.add('house')
        或者:
            map(lambda x: x.fill(self.sroom.get_house_by_hoid(x.HOid), 'house', hide=('VIid',)), room_detail_list)
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


