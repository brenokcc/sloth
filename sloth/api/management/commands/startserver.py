# -*- coding: utf-8 -*-

import os

from django.conf import settings
from django.contrib.auth.models import User
from django.core.management import call_command
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    def handle(self, *args, **options):
        call_command('sync')
        call_command('runserver', '0.0.0.0:8000', '--noreload')