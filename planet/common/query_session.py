# -*- coding: utf-8 -*-
import math

from flask import request
from sqlalchemy import inspection, log, util
from sqlalchemy.orm import Query as _Query, Session as _Session
from sqlalchemy.sql.sqltypes import NullType

from .error_response import ParamsError


@inspection._self_inspects
@log.class_logger
class Query(_Query):
    """定义查询方法"""
    def filter_without_none(self, *criterion):
        """等同于filter查询, 但是会无视双等号后为None的值
        例子: session.query(Admin).filter_without_none(Admin.ADisfreeze == freeze)
                如果freeze是None则不执行过滤
        """
        criterion = list(filter(lambda x: not isinstance(x.right.type, NullType), list(criterion)))
        if not criterion:
            return self
        return super(Query, self).filter(*criterion)

    def filter_by_(self, **kwargs):
        """
        不提取isdelete为True的记录
        """
        if 'isdelete' not in kwargs.keys():
            kwargs['isdelete'] = False
        return super(Query, self).filter_by(**kwargs)

    def all_with_page(self):
        """
        计算总页数和总数
        :return: sqlalchemy对象列表
        """
        args = request.args.to_dict()
        page = args.get('page') or 1
        count = args.get('count') or 15
        if not page and not count:
            return self.all()
        try:
            page = int(page)
            count = int(count)
        except TypeError as e:
            raise ParamsError(u'分页参数错误')
        mount = self.count()
        page_all = math.ceil(float(mount) / count)
        request.page_all = page_all
        request.mount = mount
        return self.offset((page - 1) * count).limit(count).all()

    def contain(self, cen):
        """
        使用 session.query(User).contain(User.phone=='187')
        与使用 session.query.filter(User.phone.contains('187'))的效果一致
        二者唯一不同在于: session.query(User).contain(User.age == None) 将不过滤不异常
        """
        if isinstance(cen.right.type, NullType):
            return self
        return self.filter(cen.left.contains(cen.right))

    def gt(self, cen):
        """
        使用session.query(User).filter(User.age > 13)
        类似于 session.query(User).gt(User.age == 13)
        二者唯一不同在于: session.query(User).gt(User.age == None) 将不过滤不异常
        """
        if isinstance(cen.right.type, NullType):
            return self
        return self.filter(cen.left > cen.right)

    def lt(self, cen):
        """
        使用session.query(User).filter(User.age < 13)
        类似于 session.query(User).lt(User.age == 13)
        二者唯一不同在于: session.query(User).lt(User.age == None) 将不过滤不异常
        """
        if isinstance(cen.right.type, NullType):
            return self
        return self.filter(cen.left < cen.right)

    def test(self, cen):
        """测试"""
        import ipdb
        ipdb.set_trace()


class Session(_Session):
    # 此处制定session

    def __init__(self, bind=None, autoflush=True, expire_on_commit=True,
                 _enable_transaction_accounting=True,
                 autocommit=False, twophase=False,
                 weak_identity_map=True, binds=None, extension=None,
                 enable_baked_queries=True,
                 info=None,
                 query_cls=Query):
        super(Session, self).__init__(bind, autoflush, expire_on_commit,
                                      _enable_transaction_accounting,
                                      autocommit, twophase,
                                      weak_identity_map, binds, extension,
                                      enable_baked_queries, info,
                                      query_cls)
