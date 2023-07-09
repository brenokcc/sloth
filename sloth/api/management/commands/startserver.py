# -*- coding: utf-8 -*-

import os
import multiprocessing

from django.conf import settings
from django.contrib.auth.models import User
from django.core.management import call_command
from django.core.management.base import BaseCommand


from gunicorn.app.wsgiapp import WSGIApplication


class StandaloneApplication(WSGIApplication):
    def __init__(self, app_uri, options=None):
        self.options = options or {}
        self.app_uri = app_uri
        super().__init__()

    def load_config(self):
        config = {
            key: value
            for key, value in self.options.items()
            if key in self.cfg.settings and value is not None
        }
        for key, value in config.items():
            self.cfg.set(key.lower(), value)


class Command(BaseCommand):

    def add_arguments(self, parser):
        parser.add_argument("aplication_name", nargs="*", type=str)

    def handle(self, *args, **options):
        call_command('sync')
        call_command('collectstatic', verbosity=0, interactive=False)
        application_name = os.path.basename(os.path.abspath('.'))
        if options['aplication_name']:
            application_name = options['aplication_name'][0]
        workers = (multiprocessing.cpu_count() * 2) + 1
        options = getattr(settings, 'GUNICORN', dict(bind='0.0.0.0:8000', workers=2, timeout=300))
        print('Starting gunicorn with options {}'.format(options))
        StandaloneApplication('{}.wsgi:application'.format(application_name), options).run()
