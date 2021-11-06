from django.core.management.base import BaseCommand
from django.apps import apps

class Command(BaseCommand):

    def handle(self, *args, **options):
        Setor = apps.get_model('base', 'Setor')
        Servidor = apps.get_model('base', 'Servidor')
        #Setor.objects.first().save()
        Servidor.objects.last().save()
