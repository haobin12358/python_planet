# *- coding:utf8 *-
import sys
import os
from flask import json, request
from werkzeug.exceptions import HTTPException
sys.path.append(os.path.dirname(os.getcwd()))


class BaseError(HTTPException):
    message = '系统错误'
    status = 404
    status_code = 405001

    def __init__(self, message=None, status=None, status_code=None, header=None):
        self.code = 200
        if message:
            self.message = message
        if status_code:
            self.status_code = status_code
        if status:
            self.status = status
        super(BaseError, self).__init__(message, None)

    def get_body(self, environ=None):
        body = dict(
            status=self.status,
            status_code=self.status_code,
            message=self.message
        )
        text = json.dumps(body)
        return text

    def get_headers(self, environ=None):
        return [('Content-Type', 'application/json')]