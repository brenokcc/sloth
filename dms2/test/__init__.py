# -*- coding: utf-8 -*-
import json
import requests
import base64
from django.contrib.staticfiles.testing import StaticLiveServerTestCase


class ServerTestCase(StaticLiveServerTestCase):

    def __init__(self, *args, **kwargs):
        self.authorization = None
        self.debug = False
        super().__init__(*args, **kwargs)

    def headers(self):
        if self.authorization:
            return {'Authorization': self.authorization}
        return None

    def log(self, method, url, response):
        if self.debug:
            print('{}: {}'.format(method, url))
            print(json.dumps(response.json(), indent=4, ensure_ascii=False))
            print('\n')

    def url(self, path):
        if path.startswith('/o/'):
            return '{}{}'.format(self.live_server_url, path)
        return '{}{}'.format(self.live_server_url, path)

    def get(self, path, data=None, status_code=200):
        url = self.url(path)
        response = requests.get(url, data=data, headers=self.headers())
        self.log('GET', url, response)
        self.assertEquals(response.status_code, status_code)
        return response.json()

    def post(self, path, data=None, status_code=200):
        url = self.url(path)
        response = requests.post(url, data=data, headers=self.headers())
        self.log('POST', url, response)
        self.assertEquals(response.status_code, status_code)
        return response.json()

    def put(self, path, data=None, status_code=200):
        url = self.url(path)
        response = requests.put(url, data=data, headers=self.headers())
        self.log('PUT', url, response)
        self.assertEquals(response.status_code, status_code)
        return response.json()

    def delete(self, path, data=None, status_code=200):
        url = self.url(path)
        response = requests.delete(url, data=data, headers=self.headers())
        self.log('DELETE', url, response)
        self.assertEquals(response.status_code, status_code)
        return response.json()

    def login(self, username, password):
        self.authorization = 'Basic {}'.format(
            base64.b64encode('{}:{}'.format(username, password).encode()).decode()
        )

