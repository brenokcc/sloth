from django.core.management.base import BaseCommand
from django.apps import apps
from django.contrib.auth.models import User


class Command(BaseCommand):

    def handle(self, *args, **options):
        superuser = User.objects.get(username='admin')
        administrador = User.objects.get(username='111.111.111-11')
        gestor = User.objects.get(username='222.222.222-22')
        Demanda = apps.get_model('investimentos', 'Demanda')
        qs = Demanda.objects.role_lookups('Gestor', instituicao='instituicao')
        print(qs.apply_role_lookups(superuser).count())
        print(qs.apply_role_lookups(administrador).count())
        print(qs.apply_role_lookups(gestor).count())

