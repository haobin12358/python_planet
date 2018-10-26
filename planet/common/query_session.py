# -*- coding: utf-8 -*-
# -*- coding: utf-8 -*-
import math

from flask import request
from sqlalchemy import inspection, log, util
from sqlalchemy.orm import Query as _Query, Session as _Session
from sqlalchemy.sql.sqltypes import NullType

from WeiDian.config.response import PARAMS_ERROR


def _generative(*assertions):
    """Mark a method as generative, e.g. method-chained."""

    @util.decorator
    def generate(fn, *args, **kw):
        self = args[0]._clone()
        for assertion in assertions:
            assertion(self, fn.__name__)
        fn(self, *args[1:], **kw)
        return self
    return generate


@inspection._self_inspects
@log.class_logger
class Query(_Query):
    """定义查询方法"""
    def _no_limit_offset(self, meth):
        super(Query, self)._no_limit_offset(meth)

    def _no_statement_condition(self, meth):
        super(Query, self)._no_statement_condition(meth)

    def filter_without_none(self, *criterion):
        """等同于filter查询, 但是会无视双等号后为None的值
        例子: session.query(Admin).filter_ignore_none_args(Admin.ADisfreeze == freeze)
                如果freeze是None则不执行过滤
        """
        criterion = filter(lambda x: not isinstance(x.right.type, NullType), list(criterion))
        if not criterion:
            return self
        return super(Query, self).filter(*criterion)

    def all_with_page(self, page=None, count=None):
        """
        计算总页数和总数
        :param page: 当前页码
        :param count: 页面大小
        :return: sqlalchemy对象列表
        """
        if not page and not count:
            return self.all()
        try:
            page = int(page)
            count = int(count)
        except TypeError as e:
            raise PARAMS_ERROR(u'分页参数错误')
        mount = self.count()
        page_count = math.ceil(float(mount) / count)
        request.page_count = page_count
        request.all_count = mount
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

    def filter_strip_(self, cen):
        """
        eg: self.session.query(User).filter_strip_(Trade.id == '1cee8db5f460451089181d6a2efae09')
        """
        right_value = cen.right.value
        uuid_str = right_value[:8] + '-' + right_value[8: 12] + '-' + right_value[12: 16] + '-' + right_value[16: 20] + '-' + right_value[20: ]
        cen.right.value = uuid_str
        return self.filter(cen)

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
