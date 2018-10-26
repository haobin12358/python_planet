# *- coding:utf8 *-

def get_model_return_list(model_list):
    """
    从数据库中获取到的list(列表)中每一个是一个数据库查询结果对象，
    在这里将每一个结果对象转置为dict(字典)
    :param model_list: 从数据库中直接获取到的list
    :return: 转置后的list 如果只有一個返回單個
    """
    model_return_list = []
    for item in model_list:
        item_dict = item.keys()
        model_item = {}
        for index, key in enumerate(item_dict):
            model_item[key] = item[index]
        model_return_list.append(model_item)
    return model_return_list


def get_model_return_dict(model_params):
    """
    专门处理first数据
    :param model_params:
    :return:
    """
    model_item = {}
    if model_params:
        item_dict = model_params.keys()

        for index, key in enumerate(item_dict):
            model_item[key] = model_params[index]
    return model_item
