import requests

from planet.common.error_response import SystemError


class GetLocation():
    api_url = "http://api.map.baidu.com/geocoder/v2/"

    def __init__(self, lat, lng):
        self.lat = lat
        self.lng = lng
        self.result = self.get_location()

    def get_location(self):
        res = requests.get(self.api_url, params={
            'location': '{},{}'.format(self.lat, self.lng), 'output': 'json',
            'ak': '1bdd475a06ffdb9a4f3ee021da7ae847'})
        content = res.json()
        print(content)
        if content.get('status') != 0:
            raise SystemError('数据获取失败')
        return content.get('result')


if __name__ == '__main__':
    gl = GetLocation(30.209030485232024, 120.21175250793459)
    print(gl.result)
