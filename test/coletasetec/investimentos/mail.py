from django.contrib.auth.models import User
from django.utils.html import strip_tags
from django.core.mail import EmailMultiAlternatives


MENSAGEM = '''

<b>Senhor(a) gestor(a)</b>,

<p>Seguem as informações de acesso ao Sistema de Coleta de Demandas da Rede Federal de Educação Profissional, Científica e Tecnológica – Exercício 2023.</p>

<p>URL: https://coletasetec.ifrn.edu.br/<br>
Login: {email}<br>
Senha: {senha}<br>
</p>

<p>Por questões de segurança, orienta-se que no primeiro acesso seja feita a alteração da senha. Para isso, no canto superior direito, clique nos três pontos verticais e selecione a opção “Alterar Senha”.</p>

<p>O tutorial do sistema estará disponível em https://coletasetec.ifrn.edu.br/media/tutorial/tutorial.pdf. a partir das <b>16h (horário de Brasília) do dia 03/04/2023</b>. Não deixe de acessá-lo, pois foram realizadas várias atualizações em relação à versão anterior do sistema, para aprimorar e facilitar esse processo de coleta.<p>

<p>Por fim, informamos, também, que nessa mesma data e horário o Ciclo de Demandas 2023 estará disponível para preenchimento pelas instituições.</p>

<p>Bom trabalho!</p>

<p>
Diretoria de Desenvolvimento da Rede Federal de EPCT<br>
Secretaria de Educação Profissional e Tecnológica<br>
Ministério da Educação
</p>
'''


def enviar_senha(gestor):
    senha = 'pass{}'.format(gestor.pk)
    user = User.objects.get(username=gestor.email)
    user.set_password(senha)
    user.save()
    subject = '[SETEC] Credenciais de Acesso – Sistema de Coleta de Demandas 2023'
    html_content = MENSAGEM.format(email=gestor.email, senha=senha)
    text_content = strip_tags(html_content)
    from_email = 'naoresponder@ifrn.edu.br'
    to = gestor.email
    msg = EmailMultiAlternatives(subject, text_content, from_email, [to])
    msg.attach_alternative(html_content, "text/html")
    try:
        msg.send()
        gestor.notificado = True
        gestor.save()
        print(to)
    except Exception:
        print('ERRO: ', to)
