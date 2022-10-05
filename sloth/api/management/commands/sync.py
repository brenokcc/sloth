# -*- coding: utf-8 -*-

import os
from django.conf import settings
from django.utils import termcolors
from django.contrib.auth.models import User
from django.core.management import call_command
from django.core.management.base import BaseCommand


def print_and_call(command, *args, **kwargs):
    kwargs.setdefault('interactive', True)
    print(termcolors.make_style(fg='cyan', opts=('bold',))('>>> {} {}{}'.format(
        command, ' '.join(args), ' '.join(['{}={}'.format(k, v) for k, v in list(kwargs.items())]))))
    call_command(command, *args, **kwargs)


class Command(BaseCommand):
    def handle(self, *args, **options):

        app_labels = []
        for app_label in settings.INSTALLED_APPS:
            app_labels.append(app_label.split('.')[-1])

        print_and_call('makemigrations', *app_labels)
        print_and_call('migrate')

        # if it is the production enverinoment, lets collect static files
        if os.path.exists(os.path.join(settings.BASE_DIR, 'logs')):
            print_and_call('collectstatic', clear=True, verbosity=0, interactive=False)

        if 'DEFAULT_PASSWORD' in settings.SLOTH and not User.objects.exists():
            password = settings.SLOTH['DEFAULT_PASSWORD']()
            User.objects.create_superuser('admin', password=password)
            print('Superuser "admin" with password "{}" was created.'.format(password))
