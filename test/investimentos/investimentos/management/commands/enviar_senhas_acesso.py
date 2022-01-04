from django.core.mail import send_mail
from django.core.management import BaseCommand
from ...models import Gestor
from uuid import uuid1


class Command(BaseCommand):
    def handle(self, *args, **options):
        qs = Gestor.objects.filter(user__last_login__isnull=True)
        print(qs.count())
        for gestor in qs[0:1]:
            print(gestor.email)
            senha = uuid1().hex[0:6]
            gestor.user.set_password(senha)
            gestor.user.save()
            send_mail(
                'COLETA SETEC - Senha de Acesso',
                'Caro gestor, sua senha de acesso ao sistema COLETA SETEC é {}.'.format(senha),
                'naoresponder.ifrn.edu.br',
                [gestor.email],
                fail_silently=False,
            )
