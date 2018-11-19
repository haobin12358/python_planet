# -*- coding: utf-8 -*-
from enum import Enum as _Enum
from types import DynamicClassAttribute


class Enum(_Enum):
    @classmethod
    def _missing_(cls, value):
        if value in cls._all_value():
            return cls._custom_map.get(value)
        raise ValueError("%r is not a valid %s" % (value, cls.__name__))

    @DynamicClassAttribute
    def value(self):
        """由类变量名找到状态数字"""
        res = self._value_
        if isinstance(res, tuple):
            return res[0]
        return res

    @DynamicClassAttribute
    def zh_value(self):
        """由类变量名找到汉字"""
        res = self._value_
        if isinstance(res, tuple):
            return res[1]

    @classmethod
    def _all_value(cls):
        value_dict = {}
        for member in cls._member_map_.values():
            v = member._value_
            if isinstance(v, tuple):
                value_dict.setdefault(v[0], member)
            else:
                value_dict.setdefault(v, member)
        cls._custom_map = value_dict
        return value_dict

    @classmethod
    def all_member(cls):
        return [x.name for x in cls._member_map_.values()]


if __name__ == '__main__':


    class ProductStatus(Enum):
        """商品状态"""
        usual = (0, '正常')  # 正常
        auditing = (10, '审核中')  # 审核中
        off_shelves = 60  # 下架
        all = None

    """
       使用方法:
       ProductStatus(10).name --->  auditing
       ProductStatus(10).zh_value   --->  审核中
       ProductStatus.auditing.zh_value   --> 审核中
       ProductStatus.auditing.value --> 10
    """
    print(ProductStatus.auditing.zh_value)

