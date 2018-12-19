# -*- coding: utf-8 -*-
import json
from datetime import datetime, date

from flask import current_app, Blueprint, Flask as _Flask, Request as _Request
from werkzeug.exceptions import HTTPException
from flask.json import JSONEncoder as _JSONEncoder
from flask_cors import CORS

from planet.api.v1.AActivationcode import AActivationCode
from planet.api.v1.AActivity import AActivity
from planet.api.v1.AAuth import AAuth
from planet.api.v1.AFreshManFirstOrder import AFreshManFirstOrder
from planet.api.v1.AMagicBox import AMagicBox
from planet.api.v1.ASupplizer import ASupplizer
from planet.api.v1.ATrialCommodity import ATrialCommodity
from planet.api.v1.ABrands import ABrands
from planet.api.v1.ACart import ACart
from planet.api.v1.ACategory import ACategory
from planet.api.v1.ACoupon import ACoupon
from planet.api.v1.AGuessNum import AGuessNum
from planet.api.v1.AIndex import AIndex
from planet.api.v1.AItems import AItems
from planet.api.v1.AFile import AFile
from planet.api.v1.ALogistic import ALogistic
from planet.api.v1.AOrder import AOrder
from planet.api.v1.AProduct import AProduct
from planet.api.v1.ARefund import ARefund
from planet.api.v1.AScene import AScene
from planet.api.v1.ASku import ASku
from planet.api.v1.AUser import AUser
from planet.api.v1.ANews import ANews
from planet.api.v1.AAddress import AAddress
from planet.api.v1.AApproval import Aapproval
from planet.api.v1.AQuestanswer import AQuestanswer
from planet.api.v1.AWechatShareParams import AWechatShareParams
from planet.common.request_handler import error_handler, request_first_handler
from planet.config.secret import DefaltSettig
from planet.extensions.register_ext import register_ext
from planet.extensions.loggers import LoggerHandler


class JSONEncoder(_JSONEncoder):
    """重写对象序列化, 当默认jsonify无法序列化对象的时候将调用这里的default"""
    def default(self, o):

        if hasattr(o, 'keys') and hasattr(o, '__getitem__'):
            res = dict(o)
            new_res = {k.lower(): v for k, v in res.items()}
            return new_res
        if isinstance(o, datetime):
            # 也可以序列化时间类型的对象
            return o.strftime('%Y-%m-%d %H:%M:%S')
        if isinstance(o, date):
            return o.strftime('%Y-%m-%d')
        if isinstance(o, type):
            raise o()
        if isinstance(o, HTTPException):
            raise o
        raise TypeError(repr(o) + " is not JSON serializable")


class Request(_Request):
    def on_json_loading_failed(self, e):
        from planet.common.error_response import ParamsError
        if current_app is not None and current_app.debug:
            raise ParamsError('Failed to decode JSON object: {0}'.format(e))
        raise ParamsError('参数异常')

    def get_json(self, force=False, silent=False, cache=True):
        data = self.data
        if not data:
            return
        try:
            rv = json.loads(data)
        except ValueError as e:
            if silent:
                rv = None
                if cache:
                    normal_rv, _ = self._cached_json
                    self._cached_json = (normal_rv, rv)
            else:
                rv = self.on_json_loading_failed(e)
                if cache:
                    _, silent_rv = self._cached_json
                    self._cached_json = (rv, silent_rv)
        else:
            if cache:
                self._cached_json = (rv, rv)
        return rv

    @property
    def detail(self):
        res = {
            'path': self.path,
            'method': self.method,
            'data': self.data.decode(),
            'query': self.args.to_dict(),
            'address': self.remote_addr
        }
        if self.files:
            res.setdefault('form', dict(self.files))
        return res

    @property
    def remote_addr(self):
        if 'X-Real-Ip' in self.headers:
            return self.headers['X-Real-Ip']
        return super(Request, self).remote_addr


class Flask(_Flask):
    json_encoder = JSONEncoder
    request_class = Request


def register_v1(app):
    v1 = Blueprint(__name__, 'v1', url_prefix='/api/v1')
    v1.add_url_rule('/product/<string:product>', view_func=AProduct.as_view('product'))
    v1.add_url_rule('/file/<string:file>', view_func=AFile.as_view('file'))
    v1.add_url_rule('/category/<string:category>', view_func=ACategory.as_view('category'))
    v1.add_url_rule('/cart/<string:cart>', view_func=ACart.as_view('cart'))
    v1.add_url_rule('/order/<string:order>', view_func=AOrder.as_view('order'))
    v1.add_url_rule('/sku/<string:sku>', view_func=ASku.as_view('sku'))
    v1.add_url_rule('/user/<string:user>', view_func=AUser.as_view('user'))
    v1.add_url_rule('/refund/<string:refund>', view_func=ARefund.as_view('refund'))
    v1.add_url_rule('/brand/<string:brand>', view_func=ABrands.as_view('brand'))
    v1.add_url_rule('/address/<string:address>', view_func=AAddress.as_view('address'))
    v1.add_url_rule('/items/<string:items>', view_func=AItems.as_view('items'))
    v1.add_url_rule('/scene/<string:scene>', view_func=AScene.as_view('scene'))
    v1.add_url_rule('/index/<string:index>', view_func=AIndex.as_view('index'))
    v1.add_url_rule('/news/<string:news>', view_func=ANews.as_view('news'))
    v1.add_url_rule('/logistic/<string:logistic>', view_func=ALogistic.as_view('logistic'))
    v1.add_url_rule('/coupon/<string:coupon>', view_func=ACoupon.as_view('coupon'))
    v1.add_url_rule('/approval/<string:approval>', view_func=Aapproval.as_view('approval'))
    v1.add_url_rule('/guess_num/<string:guess_num>', view_func=AGuessNum.as_view('guess_num'))
    v1.add_url_rule('/commodity/<string:commodity>', view_func=ATrialCommodity.as_view('commodity'))
    v1.add_url_rule('/activity/<string:activity>', view_func=AActivity.as_view('activity'))
    v1.add_url_rule('/qa/<string:qa>', view_func=AQuestanswer.as_view('qa'))
    v1.add_url_rule('/supplizer/<string:supplizer>', view_func=ASupplizer.as_view('supplizer'))
    v1.add_url_rule('/magicbox/<string:magicbox>', view_func=AMagicBox.as_view('magicbox'))
    v1.add_url_rule('/fresh_man/<string:fresh_man>', view_func=AFreshManFirstOrder.as_view('fresh_man'))
    v1.add_url_rule('/shareparams/<string:shareparams>', view_func=AWechatShareParams.as_view('shareparams'))
    v1.add_url_rule('/auth/<string:auth>', view_func=AAuth.as_view('auth'))
    v1.add_url_rule('/act_code/<string:act_code>', view_func=AActivationCode.as_view('act_code'))  # 激活码


    # v1.add_url_rule('/paytest', view_func=APayTest.as_view('pay'))
    # v1.add_url_rule.....
    app.register_blueprint(v1)


def create_app():
    app = Flask(__name__)
    app.config.from_object(DefaltSettig)
    register_v1(app)
    CORS(app, supports_credentials=True)
    request_first_handler(app)
    register_ext(app)
    return app

