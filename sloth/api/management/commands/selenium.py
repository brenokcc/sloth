from django.core.management.base import BaseCommand

from sloth.test.selenium import Browser


class Command(BaseCommand):

    def handle(self, *args, **options):
        b = Browser('https://google.com', headless=False)
        b.open('/')
        try:
            b.pdb()
        except KeyboardInterrupt:
            pass
        b.close()

