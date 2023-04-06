from django.core.management.base import BaseCommand

from sloth.db import ROLE_DEFINER_CLASSES


class Command(BaseCommand):

    def handle(self, *args, **options):
        for cls in ROLE_DEFINER_CLASSES:
            for obj in cls.objects.all():
                obj.persist()
