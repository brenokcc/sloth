from uuid import uuid1
from django.contrib.auth.models import User
from django.utils.html import strip_tags
from django.core.mail import EmailMultiAlternatives


MENSAGEM = '''

<b>Senhor(a) gestor(a)</b>,

<p>Seguem as informações de acesso ao <b>Sistema de Coleta de Demandas da Rede Federal de Educação Profissional, Científica e Tecnológica</b>.</p>

<p>
<i>URL</i>: <a href="https://coletasetec.ifrn.edu.br/">https://coletasetec.ifrn.edu.br/</a> <br>
<i>Login</i>: {email} <br>
<i>Senha</i>: {senha} <br>
</p>

<p>Por questões de segurança, orienta-se que no primeiro acesso seja feita a alteração da senha. Para isso, no canto superior direito do sistema, clique no e-mail da instituição e selecione a opção “Alterar Senha”.</p>

<p>Para acessar o tutorial do sistema em PDF, acesse <a href="https://coletasetec.ifrn.edu.br/media/tutorial/tutorial.pdf">https://coletasetec.ifrn.edu.br/media/tutorial/tutorial.pdf</a>.<br>
Caso prefira o tutorial no formato de vídeo, acesse <a href="https://coletasetec.ifrn.edu.br/videos/">https://coletasetec.ifrn.edu.br/videos/</a>.</p>

<p>
<b>Diretoria de Desenvolvimento da Rede Federal<br>
Secretaria de Educação Profissional e Tecnológica</b>
</p>
'''


def enviar_senha(gestor):
    senha = '123' or uuid1().hex[0:3]
    user = User.objects.get(username=gestor.email)
    user.set_password(senha)
    user.save()
    subject = '[SETEC] Credenciais de Acesso – Sistema de Coleta de Demandas'
    html_content = MENSAGEM.format(email=gestor.email, senha=senha)
    text_content = strip_tags(html_content)
    from_email = 'naoresponder.ifrn.edu.br'
    to = gestor.email
    msg = EmailMultiAlternatives(subject, text_content, from_email, [to])
    msg.attach_alternative(html_content, "text/html")
    # msg.send()
    print(html_content)
