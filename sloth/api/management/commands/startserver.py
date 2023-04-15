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
    def handle(self, *args, **options):
        call_command('sync')
        call_command('collectstatic', verbosity=0, interactive=False)
        options = dict(bind='0.0.0.0:8000', workers=(multiprocessing.cpu_count() * 2) + 1)
        StandaloneApplication("petshop.wsgi:application", options).run()