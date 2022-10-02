import socket
import sys
import os
import signal
from django.conf import settings
from django.core.management.base import BaseCommand
from django.core.management import call_command
from gunicorn.app.wsgiapp import run


class Command(BaseCommand):

    def handle(self, *args, **options):
        app = os.path.basename(settings.BASE_DIR)
        if 1:
            cmd = 'docker stop {}'.format(app)
            print(cmd)
            os.system(cmd)
        else:
            with open('{}/gunicorn.pid'.format(settings.BASE_DIR)) as pid_file:
                pid = int(pid_file.read())
                print('Killing gunicorn process with PIP {}...'.format(pid))
                os.kill(pid, signal.SIGKILL)
        if os.path.exists('/etc/nginx'):
            nginx_config_file = '/etc/nginx/conf.d/{}.conf'.format(app)
            print('Removing nignx config file {}...'.format(nginx_config_file))
            os.unlink(nginx_config_file)
            os.system('nginx -s reload')
