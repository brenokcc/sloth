import sys
import os
from sloth.conf import settings
from django.core.management import ManagementUtility


URLS_FILE_CONTENT = '''from django.urls import path, include

urlpatterns = [
    path('', include('sloth.api.urls')),
]
'''

MODELS_FILE_CONTENT = '''from sloth.db import models, role, meta
'''

ACTIONS_FILE_CONTENT = '''from sloth import actions
'''

DASHBOARD_FILE_CONTENT = '''from sloth.api.dashboard import Dashboard
from .models import *


class AppDashboard(Dashboard):

    def __init__(self, request):
        super().__init__(request)
        self.header(logo='/static/images/logo.png', title=None, text='Take your time!', shadow=False)
        self.footer(title='© 2023 Sloth', text='Todos os direitos reservados', version='1.0.0')

    def view(self):
        return self.value_set()

'''

DEPLOY_WORKFLOW_CONTENT = '''name: DEPLOY

on:
  push:
    branches: [ "main" ]
  workflow_dispatch:
jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
      - name: Deploy
        env:
          TOKEN: ${{ secrets.TOKEN }}
        run: |
          curl -X POST http://deploy.cloud.aplicativo.click/ -d '{"action": "deploy", "repository": "${{ github.repositoryUrl }}", "token": "${{ secrets.TOKEN }}"}'

'''


def startproject():
    name = os.path.basename(os.path.abspath('.'))
    ManagementUtility(['django-admin.py', 'startproject', name, '.']).execute()
    settings_path = os.path.join(name, 'settings.py')
    settings_content = open(settings_path).read().replace(
        "'django.contrib.admin'",
        "'{}', 'oauth2_provider', 'sloth.api'".format(name)
    )
    settings_append = open(settings.__file__).read().replace('# ', '')
    with open(settings_path, 'w') as file:
        file.write('{}{}'.format(settings_content, settings_append))
    urls_path = os.path.join(name, 'urls.py')
    with open(urls_path, 'w') as file:
        file.write(URLS_FILE_CONTENT)
    models_path = os.path.join(name, 'models.py')
    with open(models_path, 'w') as file:
        file.write(MODELS_FILE_CONTENT)
    actions_path = os.path.join(name, 'actions.py')
    with open(actions_path, 'w') as file:
        file.write(ACTIONS_FILE_CONTENT)
    dashboard_path = os.path.join(name, 'dashboard.py')
    with open(dashboard_path, 'w') as file:
        file.write(DASHBOARD_FILE_CONTENT)
    workflows_path = os.path.join(name, '.github', 'workflows')
    os.makedirs(workflows_path, exist_ok=True)
    deploy_workflow_path = os.path.join(workflows_path, 'deploy.yml')
    with open(deploy_workflow_path, 'w') as file:
        file.write(DEPLOY_WORKFLOW_CONTENT)


if __name__ == "__main__":
    if len(sys.argv) == 1:
        startproject()
        os.system('python3 manage.py sync')
    if len(sys.argv) == 2:
        if sys.argv[1] == 'build':
            os.system('docker build -t sloth {}'.format(os.path.dirname(__file__)))
        if sys.argv[1] == 'cloud':
            os.system('python3 {}'.format(os.path.join(os.path.dirname(__file__), 'cloud', 'server.py')))
