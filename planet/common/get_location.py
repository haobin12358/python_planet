import requests
from planet.config.secret import BAIDUMPAK
from planet.common.error_response import SystemError


class GetLocation():
    """
    api文档 http://lbsyun.baidu.com/index.php?title=webapi/guide/webservice-geocoding-abroad
    """
    api_url = "http://api.map.baidu.com/geocoder/v2/"

    def __init__(self, lat, lng):
        self.lat = lat
        self.lng = lng
        self.result = self.get_location()

    def get_location(self):

        res = requests.get(self.api_url, params={
            'location': '{},{}'.format(self.lat, self.lng), 'output': 'json',
            'ak': BAIDUMPAK})
        content = res.json()
        print(content)
        if content.get('status') != 0:
            raise SystemError('数据获取失败')
        return content.get('result')


if __name__ == '__main__':
    gl = GetLocation(30.209030485232024, 120.21175250793459)
    print(gl.result)
