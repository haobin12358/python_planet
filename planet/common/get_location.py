import json
import requests
import hashlib

from planet.config.secret import BAIDUMPAK, TencentMapKey, TencentMapSK
from planet.common.error_response import SystemError


class GetLocation():
    """
    api文档 http://lbsyun.baidu.com/index.php?title=webapi/guide/webservice-geocoding-abroad
           https://lbs.qq.com/webservice_v1/guide-gcoder.html
    """
    api_url = "http://api.map.baidu.com/geocoder/v2/"  # baidu
    url = 'https://apis.map.qq.com'  # tencent

    def __init__(self, lat, lng, map='Tencent'):
        self.lat = lat
        self.lng = lng
        if map != 'Tencent':
            self.result = self.get_location_b()
        self.result = self.get_location_t()

    def get_location_b(self):
        res = requests.get(self.api_url, params={
            'location': '{},{}'.format(self.lat, self.lng), 'output': 'json',
            'ak': BAIDUMPAK})
        content = res.json()
        print(content)
        if content.get('status') != 0:
            raise SystemError('数据获取失败')
        return self.format_userlocation_b(content.get('result'))

    def format_userlocation_b(self, result):
        return {
            'ULformattedAddress': result.get('formatted_address'),
            'ULcountry': result.get('addressComponent').get('country'),
            'ULprovince': result.get('addressComponent').get('province'),
            'ULcity': result.get('addressComponent').get('city'),
            'ULdistrict': result.get('addressComponent').get('district'),
            'ULresult': json.dumps(result),
            'ULlng': result.get('location').get('lng'),
            'ULlat': result.get('location').get('lat'),
        }

    def format_userlocation_t(self, result):
        return {
                'ULformattedAddress': result.get('formatted_addresses').get('recommend'),
                'ULcountry': result.get('address_component').get('nation'),
                'ULprovince': result.get('address_component').get('province'),
                'ULcity': result.get('address_component').get('city'),
                'ULdistrict': result.get('address_component').get('district'),
                'ULresult': json.dumps(result),
                'ULlng': result.get('location').get('lng'),
                'ULlat': result.get('location').get('lat'),
            }

    def md5_encode(self, text):
        # 创建md5对象
        hl = hashlib.md5()
        # Tips
        # 此处必须声明encode
        # 若写法为hl.update(str)  报错为： Unicode-objects must be encoded before hashing
        hl.update(text.encode(encoding='utf-8'))
        # print('MD5加密前为 ：' + text)
        res = hl.hexdigest()
        # print('MD5加密后为 ：' + res)
        return res

    def get_location_t(self):
        key = TencentMapKey
        secret_key = TencentMapSK
        # location = '30.183413980701,120.26527404785156'
        args = '/ws/geocoder/v1?key={}&location={},{}'.format(key, self.lat, self.lng)
        sig = self.md5_encode(args + secret_key)

        res = requests.get('{}{}&sig={}'.format(self.url, args, sig))
        # print(eval(res.content))
        content = res.json()
        if content.get('status') != 0:
            raise SystemError('数据获取失败')
        return self.format_userlocation_t(content.get('result'))


if __name__ == '__main__':
    gl = GetLocation(30.209030485232024, 120.21175250793459)
    print(gl.result)
