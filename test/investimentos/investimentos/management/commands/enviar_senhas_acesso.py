from django.core.mail import send_mail
from django.core.management import BaseCommand
from ...models import Gestor
from uuid import uuid1


MENSAGEM = '''
Assunto: [SETEC] Credenciais de Acesso – Sistema de Coleta de Demandas

Senhor(a) gestor(a),

Seguem as informações de acesso ao Sistema de Coleta de Demandas da Rede Federal de Educação Profissional, Científica e Tecnológica.

URL: https://coletasetec.ifrn.edu.br/
Login: {email}
Senha: {senha}

Por questões de segurança, orienta-se que no primeiro acesso seja feita a alteração da senha. Para isso, no canto superior direito do sistema, clique no e-mail da instituição e selecione a opção “Alterar Senha”. 

Para acessar o tutorial do sistema em PDF, acesse https://coletasetec.ifrn.edu.br/tutorial/tutoria.pdf.
Caso prefira o tutorial no formato de video, acesse https://coletasetec.ifrn.edu.br/videos/.

Diretoria de Desenvolvimento da Rede Federal
Secretaria de Educação Profissional e Tecnológica
'''


class Command(BaseCommand):
    def handle(self, *args, **options):
        qs = Gestor.objects.filter(user__last_login__isnull=True)
        print(qs.count())
        for gestor in qs[0:1]:
            print(gestor.email)
            senha = uuid1().hex[0:3]
            gestor.user.set_password(senha)
            gestor.user.save()
            send_mail(
                MENSAGEM.format(email=gestor.email, senha=senha),
                [gestor.email],
                fail_silently=False,
            )
