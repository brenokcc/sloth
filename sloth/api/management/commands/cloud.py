import os
import requests
from django.conf import settings
from django.core.management.base import BaseCommand

OPTIONS = 'deploy', 'update', 'backup', 'undeploy', 'destroy'

class Command(BaseCommand):
    def add_arguments(self, parser):
        for option in OPTIONS:
            parser.add_argument('--{}'.format(option), nargs='*', help='Executes {}'.format(option))

    def handle(self, *args, **options):
        url = settings.CLOUD_PROVIDER_API_URL
        token = settings.CLOUD_PROVIDER_API_TOKEN
        repository = open('.git/config').read().split('git@github.com:')[-1].split('.git')[0]
        repository = os.popen('git config --get remote.origin.url').read().strip().replace('git:', 'https:')
        print(url, repository)
        for action in OPTIONS:
            if options[action] is not None:
                break
        if action:
            data = dict(action=action, repository=repository, token=token)
            print('>>>', data)
            response = requests.post(url, json=data)
            print(response.text)
            print('<<<', response.json())
