# -*- coding: utf-8 -*-

import base64
import json

import requests
from django.contrib.auth.models import User
from django.contrib.staticfiles.testing import StaticLiveServerTestCase
from .selenium import SeleniumTestCase


class ServerTestCase(StaticLiveServerTestCase):

    def __init__(self, *args, **kwargs):
        self.authorization = None
        self.debug = False
        super().__init__(*args, **kwargs)

    def headers(self):
        if self.authorization:
            return {'Authorization': self.authorization}
        return None

    def log(self, method, url, data, response):
        if self.debug:
            print('{}: {}'.format(method, url))
            try:
                if data:
                    print('Input:\n{}'.format(json.dumps(data, indent=4, ensure_ascii=False)))
                print('Output:\n{}'.format(json.dumps(response.json(), indent=4, ensure_ascii=False)))
            except Exception:
                import traceback
                print(traceback.format_exc())
                print(data)
            print('\n')

    def url(self, path):
        if path.startswith('/o/'):
            return '{}{}'.format(self.live_server_url, path)
        return '{}{}'.format(self.live_server_url, path)

    def get(self, path, data=None, status_code=200):
        url = self.url(path)
        response = requests.get(url, data=data, headers=self.headers())
        self.log('GET', url, data, response)
        self.assertEquals(response.status_code, status_code)
        return response.json()

    def post(self, path, data=None, status_code=200):
        url = self.url(path)
        response = requests.post(url, data=data, headers=self.headers())
        self.log('POST', url, data, response)
        self.assertEquals(response.status_code, status_code)
        return response.json()

    def put(self, path, data=None, status_code=200):
        url = self.url(path)
        response = requests.put(url, data=data, headers=self.headers())
        self.log('PUT', url, data, response)
        self.assertEquals(response.status_code, status_code)
        return response.json()

    def delete(self, path, data=None, status_code=200):
        url = self.url(path)
        response = requests.delete(url, data=data, headers=self.headers())
        self.log('DELETE', url, data, response)
        self.assertEquals(response.status_code, status_code)
        return response.json()

    def login(self, username, password):
        self.authorization = 'Basic {}'.format(
            base64.b64encode('{}:{}'.format(username, password).encode()).decode()
        )

    def authorize(self, access_token):
        self.authorization = '{} {}'.format('Bearer', access_token)

    def logout(self):
        self.authorization = None

    @staticmethod
    def create_user(username, password, is_superuser=False):
        user = User.objects.create(username=username)
        user.set_password(password)
        user.is_superuser = is_superuser
        user.save()
        return user
