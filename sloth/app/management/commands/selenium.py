from django.core.management.base import BaseCommand
from sloth.test.selenium import Browser


class Command(BaseCommand):

    def handle(self, *args, **options):
        b = Browser('http://127.0.0.1:8000')
        b.open('/')
        try:
            b.pdb()
        except KeyboardInterrupt:
            pass
        b.close()

