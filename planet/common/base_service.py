# -*- coding: utf-8 -*-
import traceback
from contextlib import contextmanager

from sqlalchemy.orm import sessionmaker

from .error_response import DbError
from .base_model import Base
from .. import models
from .base_model import mysql_engine
from .query_session import Session

db_session = sessionmaker(bind=mysql_engine, class_=Session)


def get_session():
    try:
        session = db_session()
        status = True
    except Exception as e:
        print(e.message)
        session = None
        status = False
    finally:
        return session, status


def close_session(fn):
    def inner(self, *args, **kwargs):
        try:
            result = fn(self, *args, **kwargs)
            if isinstance(result, list) or isinstance(result, Base):
                self.session.expunge_all()
            self.session.commit()
            return result
        except Exception as e:
            print(u"DBERROR" + traceback.format_exc())
            # current_app.logger.error(traceback.format_exc().decode('unicode-escape'))
            self.session.rollback()
            # raise e
            raise DbError(message=e.message)
        finally:
            self.session.close()
    return inner


# service 基础类
class SBase(object):
    def __init__(self):
        try:
            self.session = db_session()
        except Exception as e:
            # raise e
            print(e.message)

    @close_session
    def add_models(self, mod):
        """
        多model添加, 可保证原子性
        :param kwargs: {model_name: data, model_name2: [data2, data21], model_name3: data ....}
        """
        model_beans = []
        for model_name, datadict_or_list in mod.items():
            if isinstance(datadict_or_list, list):
                for data_dict in datadict_or_list:
                    model_bean = self.get_model_bean(model_name, data_dict)
                    model_beans.append(model_bean)
            else:
                model_bean = self.get_model_bean(model_name, datadict_or_list)
                model_beans.append(model_bean)
        self.session.add_all(model_beans)

    @staticmethod
    def get_model_bean(model_name, data_dict):
        print(model_name)
        if not getattr(models, model_name):
            print("model name = {0} error ".format(model_name))
            return
        model_bean = eval(" models.{0}()".format(model_name))
        model_bean_key = model_bean.__table__.columns.keys()
        model_bean_key_without_line = list(map(lambda x: x.strip('_'), model_bean_key))
        lower_table_key = list(map(lambda x: x.lower().strip('_'), model_bean_key))  # 数据库的字段转小写
        for item_key in data_dict.keys():
            if item_key.lower() in lower_table_key:  # 如果json中的key同时也存在与数据库的话
                # 找到此key在model_beankey中的位置
                index = lower_table_key.index(item_key.lower())
                if data_dict.get(item_key) is not None:  # 如果传入的字段有值
                    setattr(model_bean, model_bean_key_without_line[index], data_dict.get(item_key))
        for key in model_bean.__table__.columns.keys():
            if key in data_dict:
                setattr(model_bean, key, data_dict.get(key))
        return model_bean

    @close_session
    def add_model(self, model_name, data_dict, return_fields=None):
        print(model_name)
        if not getattr(models, model_name):
            print("model name = {0} error ".format(model_name))
            return
        model_bean = eval(" models.{0}()".format(model_name))
        model_bean_key = model_bean.__table__.columns.keys()
        model_bean_key_without_line = list(map(lambda x: x.strip('_'), model_bean_key))
        lower_table_key = list(map(lambda x: x.lower().strip('_'), model_bean_key))  # 数据库的字段转小写
        for item_key in data_dict.keys():
            if item_key.lower() in lower_table_key:  # 如果json中的key同时也存在与数据库的话
                # 找到此key在model_beankey中的位置
                index = lower_table_key.index(item_key.lower())
                if data_dict.get(item_key) is not None:  # 如果传入的字段有值
                    setattr(model_bean, model_bean_key_without_line[index], data_dict.get(item_key))
        for key in model_bean.__table__.columns.keys():
            if key in data_dict:
                setattr(model_bean, key, data_dict.get(key))
        model_bean_dict = dict(model_bean.clean.add(*return_fields)) if return_fields else None
        self.session.add(model_bean)
        return model_bean_dict

    @contextmanager
    def auto_commit(self, func=None, args=[]):
        try:
            yield self.session
            self.session.commit()
            self.session.close()
        except Exception as e:
            if func is not None:
                func(*args)
            self.session.rollback()
            raise e
        finally:
            self.session.close()