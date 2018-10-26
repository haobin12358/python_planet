# *- coding:utf8 *-
# 兼容linux系统
import sys
import os

from flask import current_app

sys.path.append(os.path.dirname(os.getcwd()))  # 增加系统路径
sys.path.append(os.path.dirname(os.getcwd()))  # 增加系统路径
import WeiDian.models.model as models


# 装饰器，用来解析数据库获取的内容，将获取到的对象转置为dict，将获取到的单个数据的tuple里的数据解析出来
def trans_params(func):
    def inner(*args, **kwargs):
        params = func(*args, **kwargs)
        result = []
        if params:
            for param in params:
                if isinstance(param, (list, tuple)):
                    data = param[0]
                    # 如果发现解析的数据是Unicode 转置为utf-8
                    if isinstance(data, unicode):
                        data = data.encode("utf8")
                    result.append(data)
                elif isinstance(param, models.Base):
                    param_dict = param.__dict__
                    for param_key in param_dict:
                        # 所有的model的dict里都有这个不需要的参数，所以删除掉
                        if param_key == "_sa_instance_state":
                            continue
                        # 如果发现解析到的数据是Unicode 转置为utf-8
                        if isinstance(param_dict.get(param_key), unicode):
                            param_dict[param_key] = param_dict.get(param_key).encode("utf8")

                    result.append(param_dict)
                else:
                    result = params
        return result

    return inner


def add_model(model_name, **kwargs):
    print(model_name)
    if not getattr(models, model_name):
        print("model name = {0} error ".format(model_name))
        return
    model_bean = eval(" models.{0}()".format(model_name))
    for key in model_bean.__table__.columns.keys():
        if key in kwargs:
            if kwargs.get(key):  # 如果传入的字段有值
                setattr(model_bean, key, kwargs.get(key))
    from WeiDian.service.DBSession import get_session
    session, status = get_session()
    if status:
        session.add(model_bean)
        session.commit()
        session.close()
        return
    raise Exception("session connect error")


def add_models(model_name, **kwargs):
    """
    kwargs的格式为:
    {
        'data': [
            {
                key: value,
                ...
            },
            {
                key: value,
                key: value,
                ...
            }
        ]
    }
    """
    print(model_name)
    if not getattr(models, model_name):
        print("model name = {0} error ".format(model_name))
        return
    model_bean_list = []  # 初始化一个列表, 以便稍后使用add_all
    items = kwargs['data']
    for item in items:
        model_bean = eval(" models.{0}()".format(model_name))  # 创建
        for key in model_bean.__table__.columns.keys():
            if key in item:
                if item.get(key):
                    setattr(model_bean, key, item.get(key))
        model_bean_list.append(model_bean)
    from WeiDian.service.DBSession import get_session
    session, status = get_session()
    if status:
        session.add_all(model_bean_list)
        session.commit()
        session.close()
        return
    raise Exception("session connect error")


def list_add_models(model_name, items):
    """将一个字典列表插入到数据库
    参数最下方测试, 会忽略不存在的值, """
    model_bean_list = []  # 初始化一个列表, 以便稍后使用add_all

    for item in items:
        if not getattr(models, model_name):
            print("model name = {0} error ".format(model_name))
            return
        model_bean = eval(" models.{0}()".format(model_name))
        model_bean_key = model_bean.__table__.columns.keys()
        model_bean_key_without_line = list(map(lambda x: x.strip('_'), model_bean_key))
        lower_table_key = list(map(lambda x: x.lower().strip('_'), model_bean_key))   # 数据库的字段转小写
        for item_key in item.keys():
            if item_key.lower() in lower_table_key:  # 如果json中的key同时也存在与数据库的话
                # 找到此key在model_beankey中的位置
                index = lower_table_key.index(item_key.lower())
                if item.get(item_key) is not None:  # 如果传入的字段有值
                    setattr(model_bean, model_bean_key_without_line[index], item.get(item_key))
            model_bean_list.append(model_bean)
    from WeiDian.service.DBSession import get_session
    session, status = get_session()
    if status:
        session.add_all(model_bean_list)
        session.commit()
        session.close()
        return
    raise Exception("session connect error")


def dict_add_models(model_name, item):
    if not getattr(models, model_name):
        print("model name = {0} error ".format(model_name))
        return
    model_bean = eval(" models.{0}()".format(model_name))
    model_bean_key = model_bean.__table__.columns.keys()
    model_bean_key_without_line = list(map(lambda x: x.strip('_'), model_bean_key))
    lower_table_key = list(map(lambda x: x.lower().strip('_'), model_bean_key))   # 数据库的字段转小写
    for item_key in item.keys():
        if item_key.lower() in lower_table_key:  # 如果json中的key同时也存在与数据库的话
            # 找到此key在model_beankey中的位置
            index = lower_table_key.index(item_key.lower())
            if item.get(item_key) is not None:  # 如果传入的字段有值
                setattr(model_bean, model_bean_key_without_line[index], item.get(item_key))
    from WeiDian.service.DBSession import get_session
    session, status = get_session()
    if status:
        session.add(model_bean)
        session.commit()
        session.close()
        return
    raise Exception("session connect error")


if __name__ == '__main__':

    def test_list_add():
        import uuid
        pid = str(uuid.uuid1())
        print pid
        items = [
            {
                'prid': pid,
                "prname": "这是商品名字1",
                "prmainpic": "http://mainpic.com",
                "prtitle": "titles",
                "images": [
                    {
                        "piurl": "http://www.prurl.com",
                        "prsort": 1
                    },
                    {
                        "piurl": "'http://www.prurl2.com'",
                        "prsort": 2
                    }
                ],

                "sku": [
                    {
                            "selector": {
                                "size": "XL",
                                "color": "yellow"
                            },
                            "count": 20,
                            "header": "'图片'",
                            "price": 111.11
                    },

                    {
                            "selector": {
                                "size": "M",
                                "color": "green"
                            },
                            "count": 20,
                            "header": "'图片'",
                            "price": 89.11
                    }
                ]
            },
            {
                'prid': 'priddd',
                "prname": "这是商品名字2",
                "prmainpic": "http://mainpic.com",
                "prtitle": "titles" ,
                "images": [
                    {
                        "piurl": "'http://www.prurl.com'",
                        "prsort": 1
                    },
                    {
                        "piurl": "'http://www.prurl2.com'",
                        "prsort": 2
                    }
                ],

                "sku": [
                    {
                            "selector": {
                                "size": "XL",
                                "color": "yellow"
                            },
                            "count": 20,
                            "header": "图片",
                            "price": 111.11
                    }
                ]
            }
        ]
        list_add_models('Product', items)

    def test_dict_add():
        import uuid
        pid = str(uuid.uuid1())
        item = {
                'prid': pid,
                "prname": "ddddddddddddddddd",
                "prmainpic": "http://mainpic.com",
                "prtitle": "titles",
                "images": [
                    {
                        "piurl": "http://www.prurl.com",
                        "prsort": 1
                    },
                    {
                        "piurl": "'http://www.prurl2.com'",
                        "prsort": 2
                    }
                ],

                "sku": [
                    {
                            "selector": {
                                "size": "XL",
                                "color": "yellow"
                            },
                            "count": 20,
                            "header": "'图片'",
                            "price": 111.11
                    },

                    {
                            "selector": {
                                "size": "M",
                                "color": "green"
                            },
                            "count": 20,
                            "header": "'图片'",
                            "price": 89.11
                    }
                ]
            }
        dict_add_models('Product', item)


    test_dict_add()
