import requests


class GetLocation():
    api_url = "http://api.map.baidu.com/geocoder/v2/"

    def __init__(self, lat, lng, **kwargs):
        self.lat = lat
        self.lng = lng
        if kwargs.get('usid'):
            self.usid = kwargs.get('usid')

    def get_location(self):
        requests.get(self.api_url, params={'location': '{},{}'.format(self.lng, self.lat), 'output': 'json', '':''})
