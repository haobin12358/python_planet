# *- coding:utf8 *-
from datetime import datetime

from config.response import NOT_FOUND
from sqlalchemy import orm
from sqlalchemy.ext.declarative import declarative_base, AbstractConcreteBase

from common.timeformat import format_for_db

Base = declarative_base()


def auto_createtime(f):
    def inner(self, *args, **kwargs):
        res = f(self, *args, **kwargs)
        self.auto_creatdatatime()
        return res
    return inner


class BaseModel(AbstractConcreteBase, Base):
    __table_args__ = {"useexisting": True}

    def __getitem__(self, item):
        if hasattr(self, item):
            return getattr(self, item)
        return []

    def keys(self):
        return self.fields

    def hide(self, *keys):
        for key in keys:
            if key in self.fields:
                self.fields.remove(key)
        return self

    def add(self, *keys):
        for key in keys:
            self.fields.append(key)
        return self

    @property
    def clean(self):
        self.fields = []
        return self

    @property
    def all(self):
        return self.__table__.columns.keys()

    @orm.reconstructor
    @auto_createtime
    def __init__(self):
        self.fields = []

    def auto_creatdatatime(self):
        createtimes = filter(lambda k: 'createtime' in k, self.__table__.columns.keys())
        if createtimes:
            createtime = createtimes[0]
            existsed_time = getattr(self, createtime)
            if not existsed_time:
                setattr(self, createtime, datetime.strftime(datetime.now(), format_for_db))


    def fill(self, obj, name, hide=None, fields=None, allow_none=True):
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
            raise NOT_FOUND(msg)
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

    class Meta:
        abstract = True
