import os
import requests
from django.core.management.base import BaseCommand

OPTIONS = 'deploy', 'update', 'backup', 'undeploy', 'destroy'

class Command(BaseCommand):
    def add_arguments(self, parser):
        for option in OPTIONS:
            parser.add_argument('--{}'.format(option), nargs='*', help='Executes {}'.format(option))

    def handle(self, *args, **options):
        url = 'http://deploy.cloud.aplicativo.click'
        if 0 and os.path.exists('/Users/breno/'):
            url = 'http://127.0.0.1:9999'
        user, project_name = open('.git/config').read().split('git@github.com:')[-1].split('.git')[0].split('/')
        print(url, user, project_name)
        for action in OPTIONS:
            if options[action] is not None:
                break
        if action:
            data = dict(action=action, user=user, project_name=project_name, token='')
            print('>>>', data)
            response = requests.post(url, json=data)
            print('<<<', response.json())
