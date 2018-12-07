# -*- coding: utf-8 -*-
import math

from flask import request
from sqlalchemy import inspection, log, util
from sqlalchemy.orm import Query as _Query, Session as _Session
from sqlalchemy.sql.sqltypes import NullType

from .error_response import ParamsError, NotFound, SystemError


@inspection._self_inspects
@log.class_logger
class Query(_Query):
    """定义查询方法"""
    def filter_without_none(self, *criterion):
        """等同于filter查询, 但是会无视双等号后为None的值
        例子: session.query(Admin).filter_without_none(Admin.ADisfreeze == freeze)
                如果freeze是None则不执行过滤
        """
        # new_criterion = []
        # for criterion in list(criterion):
        #     if self._right_not_none(criterion):
        #         new_criterion.append(criterion)
        criterion = list(filter(self._right_not_none, list(criterion)))
        return super(Query, self).filter(*criterion)

    def _right_not_none(self, x):
        if hasattr(x, 'right'):
            if hasattr(x.right, 'element'):
                # 对in查询的过滤
                return len(x.right.element)
            return not isinstance(x.right.type, NullType)
        return True

    def filter_by_(self, *args, **kwargs):
        """
        不提取isdelete为True的记录
        """
        for arg in args:
            kwargs.update(arg)
        if 'isdelete' not in kwargs.keys():
            kwargs['isdelete'] = False
        kwargs = {k: v for k, v in kwargs.items() if v is not None}
        return super(Query, self).filter_by(**kwargs)

    def filter_by(self, *args, **kwargs):
        for arg in args:
            kwargs.update(arg)
        kwargs = {k: v for k, v in kwargs.items()}
        return super(Query, self).filter_by(**kwargs)

    def first_(self, error=None):
        """不存在就报错"""
        res = super(Query, self).first()
        if res or error is None:
            return res
        raise NotFound(error)

    def delete_(self, synchronize_session='evaluate', update_args=None):
        """执行delete操作的时候不要使用"""
        return self.update({'isdelete': True}, synchronize_session=synchronize_session, update_args=update_args)

    def delete(self, synchronize_session='evaluate'):
        raise SystemError("do not use delete")

    def filter_(self, *args, **kwargs):
        return self.filter_without_none(*args)

    def all_with_page(self):
        """
        计算总页数和总数
        :return: sqlalchemy对象列表
        """
        args = request.args.to_dict()
        page = args.get('page_num') or 1
        count = args.get('page_size') or 15
        # assert int(count) <= 20, 'page_size建议不超过20'
        if not page and not count:
            return self.all()
        try:
            page = int(page)
            count = int(count)
        except TypeError as e:
            raise ParamsError(u'分页参数错误')
        mount = self.distinct().count()  # 未知的计数错误
        page_all = math.ceil(float(mount) / count)
        request.page_all = page_all
        request.mount = mount
        return self.distinct().offset((page - 1) * count).limit(count).all()

    def all_(self, page=None):
        if page:
            return self.all_with_page()
        else:
            return self.all()

    def contain(self, cen):
        """
        使用 session.query(User).contain(User.phone=='187')
        与使用 session.query.filter(User.phone.contains('187'))的效果一致
        二者唯一不同在于: session.query(User).contain(User.age == None) 将不过滤不异常
        """
        if isinstance(cen.right.type, NullType):
            return self
        return self.filter(cen.left.contains(cen.right))

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
