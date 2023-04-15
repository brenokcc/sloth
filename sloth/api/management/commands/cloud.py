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
        if os.path.exists('/Users/breno/'):
            pass # url = 'http://127.0.0.1:9999'
        repository = open('.git/config').read().split('git@github.com:')[-1].split('.git')[0]
        print(url, repository)
        for action in OPTIONS:
            if options[action] is not None:
                break
        if action:
            data = dict(action=action, repository='https://github.com/{}.git'.format(repository), token='6a18bca8-0ad1-4857-afe3-f32e639fd2d6')
            print('>>>', data)
            response = requests.post(url, json=data)
            print('<<<', response.json())
