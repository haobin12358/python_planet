# -*- coding: utf-8 -*-
import qiniu as QiniuClass


class QiniuStorage(object):
    """
    官方SDK文档 https://developer.qiniu.com/kodo/sdk/1242/python
    """
    def __init__(self, app=None):
        self.app = app
        if app is not None:
            self.init_app(app)

    def init_app(self, app):
        self.access_key = app.config.get('QINIU_ACCESS_KEY', '')
        self.secret_key = app.config.get('QINIU_SECRET_KEY', '')
        self.bucket_name = app.config.get('QINIU_BUCKET_NAME', '')
        self.domain = app.config.get('')

    def save(self, data, filename=None):
        auth = QiniuClass.Auth(self.access_key, self.secret_key)
        token = auth.upload_token(self.bucket_name)
        return QiniuClass.put_file(token, filename, data)

    def delete(self, filename):
        auth = QiniuClass.Auth(self.access_key, self.secret_key)
        bucket = QiniuClass.BucketManager(auth)
        return bucket.delete(self.bucket_name, filename)

    def url_to_storage(self, url, filename):
        auth = QiniuClass.Auth(self.access_key, self.secret_key)
        bucket = QiniuClass.BucketManager(auth)
        return bucket.fetch(url, self.bucket_name, filename)


# if __name__ == '__main__':
#     q = QiniuStorage()
#     ret, info = q.save('/home/wiilz/Desktop/JjfxnGdM7jSKIJGrMuvyd702def0-403a-11e9-b2cf-00163e13a3e3.jpeg_3225x2033.jpeg', 'first_picture')
#     print(ret)
