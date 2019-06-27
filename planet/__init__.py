# -*- coding: utf-8 -*-
import json
from datetime import datetime, date
from decimal import Decimal

from flask import current_app, Blueprint, Flask as _Flask, Request as _Request
from flask_socketio import SocketIO
from werkzeug.exceptions import HTTPException
from flask.json import JSONEncoder as _JSONEncoder
from flask_cors import CORS

from planet.api.v2.AScenicSpot import AScenicSpot
from planet.api.v2.APlay import APlay
from planet.api.v2.AGuessGroup import AGuessGroup
from planet.api.v2.AIntegral import AIntegral
from planet.api.v2.ACollection import ACollection
from planet.api.v2.ASetSupper import ASetSupper
from planet.api.v2.AActivationcode import AActivationCode
from planet.api.v2.AActivity import AActivity
from planet.api.v2.AAuth import AAuth
from planet.api.v2.ACommision import ACommission
from planet.api.v2.AExcel import AExcel
from planet.api.v2.AFreshManFirstOrder import AFreshManFirstOrder
from planet.api.v2.AMagicBox import AMagicBox
from planet.api.v2.ASupplizer import ASupplizer
from planet.api.v2.ATimeLimited import ATimelimited
from planet.api.v2.ATrialCommodity import ATrialCommodity
from planet.api.v2.ABrands import ABrands
from planet.api.v2.ACart import ACart
from planet.api.v2.ACategory import ACategory
from planet.api.v2.ACoupon import ACoupon
from planet.api.v2.AGuessNum import AGuessNum
from planet.api.v2.AIndex import AIndex
from planet.api.v2.AItems import AItems
from planet.api.v2.AFile import AFile
from planet.api.v2.ALogistic import ALogistic
from planet.api.v2.AOrder import AOrder
from planet.api.v2.AProduct import AProduct
from planet.api.v2.ARefund import ARefund
from planet.api.v2.AScene import AScene
from planet.api.v2.ASku import ASku
from planet.api.v2.AUser import AUser
from planet.api.v2.ANews import ANews
from planet.api.v2.AAddress import AAddress
from planet.api.v2.AApproval import Aapproval
from planet.api.v2.AQuestanswer import AQuestanswer
from planet.api.v2.AWechatShareParams import AWechatShareParams
from planet.api.v2.ASigninSetting import ASigninSetting
from planet.api.v2.AClub import AClub
from planet.api.v2.ATest import ATest

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
        if isinstance(o, Decimal):
            return round(float(o), 2)
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
            'data': self.data,
            'query': self.args.to_dict(),
            'address': self.remote_addr
        }
        # if self.files:
        #     res.setdefault('files', dict(self.files))
        return res

    @property
    def remote_addr(self):
        if 'X-Real-Ip' in self.headers:
            return self.headers['X-Real-Ip']
        return super(Request, self).remote_addr


class Flask(_Flask):
    json_encoder = JSONEncoder
    request_class = Request


def register(app):
    v2 = Blueprint(__name__, 'v2', url_prefix='/api/v2')
    v2.add_url_rule('/product/<string:product>', view_func=AProduct.as_view('product'))
    v2.add_url_rule('/file/<string:file>', view_func=AFile.as_view('file'))
    v2.add_url_rule('/category/<string:category>', view_func=ACategory.as_view('category'))
    v2.add_url_rule('/cart/<string:cart>', view_func=ACart.as_view('cart'))
    v2.add_url_rule('/order/<string:order>', view_func=AOrder.as_view('order'))
    v2.add_url_rule('/sku/<string:sku>', view_func=ASku.as_view('sku'))
    v2.add_url_rule('/user/<string:user>', view_func=AUser.as_view('user'))
    v2.add_url_rule('/refund/<string:refund>', view_func=ARefund.as_view('refund'))
    v2.add_url_rule('/brand/<string:brand>', view_func=ABrands.as_view('brand'))
    v2.add_url_rule('/address/<string:address>', view_func=AAddress.as_view('address'))
    v2.add_url_rule('/items/<string:items>', view_func=AItems.as_view('items'))
    v2.add_url_rule('/scene/<string:scene>', view_func=AScene.as_view('scene'))
    v2.add_url_rule('/index/<string:index>', view_func=AIndex.as_view('index'))
    v2.add_url_rule('/news/<string:news>', view_func=ANews.as_view('news'))
    v2.add_url_rule('/logistic/<string:logistic>', view_func=ALogistic.as_view('logistic'))
    v2.add_url_rule('/coupon/<string:coupon>', view_func=ACoupon.as_view('coupon'))
    v2.add_url_rule('/approval/<string:approval>', view_func=Aapproval.as_view('approval'))
    v2.add_url_rule('/guess_num/<string:guess_num>', view_func=AGuessNum.as_view('guess_num'))
    v2.add_url_rule('/commodity/<string:commodity>', view_func=ATrialCommodity.as_view('commodity'))
    v2.add_url_rule('/activity/<string:activity>', view_func=AActivity.as_view('activity'))
    v2.add_url_rule('/qa/<string:qa>', view_func=AQuestanswer.as_view('qa'))
    v2.add_url_rule('/supplizer/<string:supplizer>', view_func=ASupplizer.as_view('supplizer'))
    v2.add_url_rule('/magicbox/<string:magicbox>', view_func=AMagicBox.as_view('magicbox'))
    v2.add_url_rule('/fresh_man/<string:fresh_man>', view_func=AFreshManFirstOrder.as_view('fresh_man'))
    v2.add_url_rule('/shareparams/<string:shareparams>', view_func=AWechatShareParams.as_view('shareparams'))
    v2.add_url_rule('/auth/<string:auth>', view_func=AAuth.as_view('auth'))
    v2.add_url_rule('/act_code/<string:act_code>', view_func=AActivationCode.as_view('act_code'))  # 激活码
    v2.add_url_rule('/commision/<string:comm>', view_func=ACommission.as_view('comm'))  # 佣金设置
    v2.add_url_rule('/siginsetting/<string:siginsetting>', view_func=ASigninSetting.as_view('siginsetting'))  # 签到设置
    v2.add_url_rule('/excel/<string:excel>', view_func=AExcel.as_view('excel'))  # 签到设置
    v2.add_url_rule('/club/<string:club>', view_func=AClub.as_view('club'))  # 官网相关
    v2.add_url_rule('/test/<string:test>', view_func=ATest.as_view('test'))  # 测试
    v2.add_url_rule('/timelimited/<string:timelimited>', view_func=ATimelimited.as_view('timelimited'))  # 限时活动
    v2.add_url_rule('/integral/<string:integral>', view_func=AIntegral.as_view('integral'))  # 星币商城
    v2.add_url_rule('/setsupper/<string:setsupper>', view_func=ASetSupper.as_view('setsupper'))  # 设置邀请人
    v2.add_url_rule('/collection/<string:collection>', view_func=ACollection.as_view('collection'))  # 设置收藏
    v2.add_url_rule('/scenicspot/<string:scenicspot>', view_func=AScenicSpot.as_view('scenicspot'))  # 景区
    v2.add_url_rule('/guessgroup/<string:guessgroup>', view_func=AGuessGroup.as_view('guessgroup'))  # 拼团竞猜
    v2.add_url_rule('/play/<string:play>', view_func=APlay.as_view('play'))  # 活动

    # v2.add_url_rule('/paytest', view_func=APayTest.as_view('pay'))
    # v2.add_url_rule.....
    app.register_blueprint(v2)


def create_app():
    app = Flask(__name__)
    socket = SocketIO(app)
    app.config.from_object(DefaltSettig)
    register(app)
    CORS(app, supports_credentials=True)
    request_first_handler(app)
    register_ext(app)
    error_handler(app)
    return app, socket
