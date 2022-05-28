from django.core.management.base import BaseCommand
from django.apps import apps
from sloth.api.models import Role
from sloth.db import ROLE_DEFINER_CLASSES


class Command(BaseCommand):

    def handle(self, *args, **options):
        for cls in ROLE_DEFINER_CLASSES:
            for obj in cls.objects.all():
                obj.persist()
