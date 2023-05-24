import os
import json
import onetimepass
import base64
import requests
import io
import subprocess
from django.core.cache import cache
from django.core.exceptions import ValidationError
from django.http import HttpResponseRedirect
from django.contrib.auth.models import User
from django.core.management import call_command
from sloth import actions, meta
from django.contrib import auth
from django.conf import settings
from .models import AuthCode, PushNotification
from ..utils.http import CsvResponse, XlsResponse, PdfReportResponse
from ..utils.icons import bootstrap, materialicons, fontawesome


class DeleteUserRole(actions.Action):
    class Meta:
        verbose_name = 'Excluir'
        style = 'danger'

    def submit(self):
        self.instance.delete()
        self.redirect()


class InactivateUserRole(actions.Action):
    class Meta:
        verbose_name = 'Excluir'
        style = 'danger'

    def submit(self):
        self.instance.active = False
        self.instance.save()
        self.redirect()


class ActivateUserRole(actions.Action):
    class Meta:
        verbose_name = 'Ativar'
        style = 'success'

    def submit(self):
        self.instance.active = True
        self.instance.save()
        self.redirect('.')

    def has_permission(self, user):
        return user.is_superuser and not self.instance.active


class DeactivateUserRole(actions.Action):
    class Meta:
        verbose_name = 'Desativar'
        style = 'warning'

    def submit(self):
        self.instance.active = False
        self.instance.save()
        self.redirect()

    def has_permission(self, user):
        return user.is_superuser and self.instance.active


class LoginAsUser(actions.Action):
    class Meta:
        icon = 'unlock'
        verbose_name = 'Acessar'
        style = 'warning'

    def view(self):
        self.alert('Ao confirmar essa ação, você será autenticado com o usuário selecionado.')

    def submit(self):
        auth.login(self.request, self.instance)
        self.redirect('/')

    def has_permission(self, user):
        return user.is_superuser and self.instance != self.request.user


class StopTask(actions.Action):
    class Meta:
        icon = 'stop-circle'
        verbose_name = 'Parar Execução'
        style = 'danger'
        confirmation = True

    def submit(self):
        self.instance.stop()
        cache.set('task_{}_stopped'.format(self.instance.id), True)
        self.message()
        self.redirect()

    def has_permission(self, user):
        return self.instance.in_progress() and (user.is_superuser or self.instance.user == user)


class Login(actions.ActionView):
    username = actions.CharField(label='Login')
    password = actions.CharField(label='Senha', widget=actions.PasswordInput())
    auth_code = actions.CharField(label='Código', widget=actions.PasswordInput(), required=False)

    class Meta:
        ajax = False
        submit_label = 'Acessar'
        fieldsets = {
            None: ('username', 'password', 'auth_code'),
        }

    def __init__(self, *args, **kwargs):
        self.user = None
        super().__init__(*args, **kwargs)
        if cache.get('login', {}).get('mask'):
            self.fields['username'].widget.mask = cache.get('login', {}).get('mask')
        self.show('auth_code') if self.requires_2fa() else self.hide('auth_code')

    def get_verbose_name(self):
        return cache.get('login', {}).get('title')

    def get_image(self):
        return cache.get('login', {}).get('logo')

    def view(self):
        if 'o' in self.request.GET:
            provider = settings.OAUTH2_AUTHENTICATORS[self.request.GET['o'].upper()]
            authorize_url = '{}?response_type=code&client_id={}&redirect_uri={}'.format(
                provider['AUTHORIZE_URL'], provider['CLIENTE_ID'], provider['REDIRECT_URI']
            )
            if provider.get('SCOPE'):
                authorize_url = '{}&scope={}'.format(authorize_url, provider.get('SCOPE'))
            self.request.session['o'] = self.request.GET['o']
            self.request.session.save()
            self.redirect(authorize_url)
        elif 'code' in self.request.GET:
            provider = settings.OAUTH2_AUTHENTICATORS[self.request.session['o'].upper()]
            access_token_request_data = dict(
                grant_type='authorization_code', code=self.request.GET.get('code'), redirect_uri=provider['REDIRECT_URI'],
                client_id=provider['CLIENTE_ID'], client_secret=provider['CLIENT_SECRET']
            )
            data = json.loads(
                requests.post(provider['ACCESS_TOKEN_URL'], data=access_token_request_data, verify=False).text
            )
            headers = {
                'Authorization': 'Bearer {}'.format(data.get('access_token')), 'x-api-key': provider['CLIENT_SECRET']
            }

            if provider.get('USER_DATA_METHOD', 'GET').upper() == 'POST':
                response = requests.post(provider['USER_DATA_URL'], data={'scope': data.get('scope')}, headers=headers)
            else:
                response = requests.get(provider['USER_DATA_URL'], data={'scope': data.get('scope')}, headers=headers)
            if response.status_code == 200:
                data = json.loads(response.text)
                username = data[provider['USER_DATA']['USERNAME']]
                user = User.objects.filter(username=username).first()
                if user is None and provider.get('USER_AUTO_CREATE'):
                    user = User.objects.create(
                        username=username,
                        email=data[provider['USER_DATA']['EMAIL']] if provider['USER_DATA']['EMAIL'] else '',
                        first_name=data[provider['USER_DATA']['FIRST_NAME']] if provider['USER_DATA']['FIRST_NAME'] else '',
                        last_name=data[provider['USER_DATA']['LAST_NAME']] if provider['USER_DATA']['LAST_NAME'] else ''
                    )
                if user:
                    auth.login(self.request, user)
                    self.redirect('/app/dashboard/')
                else:
                    self.message('Usuário "{}" inexistente.'.format(username), 'warning')
                    self.redirect('/app/dashboard/login/')
            else:
                self.info('Acesso não autorizado.')

    def requires_2fa(self, username=None):
        return AuthCode.objects.filter(user__username=self.data.get('username', username), active=True).exists()

    def on_username_change(self, username):
        self.show('auth_code') if self.requires_2fa() else self.hide('auth_code')

    def clean(self):
        if self.cleaned_data:
            username = self.cleaned_data.get('username')
            password = self.cleaned_data.get('password')
            auth_code = self.cleaned_data.get('auth_code')
            if username and password:
                self.user = auth.authenticate(
                    self.request, username=username, password=password
                )
                if self.user is None:
                    raise actions.ValidationError('Login e senha não conferem.')
            if self.user and self.requires_2fa():
                user_auth_code = self.user.authcode_set.values_list('secret', flat=True).first()
                if not onetimepass.valid_totp(auth_code, user_auth_code):
                    raise actions.ValidationError('Código de autenticação inválido.')
        return self.cleaned_data

    def submit(self):
        if self.user:
            auth.login(self.request, self.user, backend='django.contrib.auth.backends.ModelBackend')
            self.redirect('/app/dashboard/')

    def has_permission(self, user):
        return True

    def get_alternative_links(self):
        links = []
        for name in cache.get('login', {}).get('actions', ()):
            action = actions.ACTIONS[name](request=self.request)
            links.append(dict(
                label=action.get_verbose_name(),
                image=None,
                url='/app/dashboard/{}/'.format(name),
                popup=action.get_metadata()['modal'],
            )
        )
        for name, authenticator in settings.OAUTH2_AUTHENTICATORS.items():
            if authenticator['CLIENTE_ID']:
                links.append(dict(
                    label = authenticator['TEXT'],
                    image = authenticator['LOGO'],
                    url='/app/dashboard/login/?o={}'.format(name),
                    popup=False
                )
            )
        return links


class ChangePassword(actions.ActionView):
    password = actions.CharField(label='Senha', widget=actions.PasswordInput())
    password2 = actions.CharField(label='Confirmação', widget=actions.PasswordInput())

    class Meta:
        modal = True
        icon = 'input-cursor-text'
        verbose_name = 'Alterar Senha'

    def clean(self):
        password = self.cleaned_data.get('password')
        password2 = self.cleaned_data.get('password2')
        if password != password2:
            raise actions.ValidationError('Senhas não conferem.')

        if settings.FORCE_PASSWORD_DEFINITION:
            default_password = settings.DEFAULT_PASSWORD(self.request.user)
            if self.request.user.check_password(default_password) and self.request.user.check_password(password):
                raise actions.ValidationError('Senha não pode ser a senha padrão.')

        return self.cleaned_data

    def submit(self):
        self.request.user.set_password(self.cleaned_data.get('password'))
        self.request.user.save()
        auth.login(self.request, self.request.user, backend='django.contrib.auth.backends.ModelBackend')
        self.message()
        self.redirect()

    def has_permission(self, user):
        return user.is_superuser or self.request.user == user


class Logout(actions.ActionView):
    class Meta:
        verbose_name = 'Sair'
        ajax = False

    def view(self):
        self.request.session.clear()
        auth.logout(self.request)
        self.redirect('/')

    def has_permission(self, user):
        return True


class Activate2fAuthentication(actions.Action):
    code = actions.CharField(label='Código')

    class Meta:
        modal = True
        verbose_name = 'Ativar Autentição 2FA'

    @meta('QrCode', renderer='utils/qrcode')
    def get_qrcode(self):
        auth_code = self.request.user.authcode_set.first()
        if auth_code is None:
            auth_code = AuthCode.objects.create(
                user=self.request.user, secret=base64.b32encode(os.urandom(10)).decode('utf-8')
            )
        url = 'otpauth://totp/Agenda:{}?secret={}&issuer=Agenda'.format(
            self.request.user.username, auth_code.secret
        )
        return url

    def view(self):
        self.info('''Para ativar a autenticação de dois fatores,
        baixe o aplicativo (Google Authenticator, Duo Mobile, etc)
        e escaneio o QrCode exibido na tela. Em seguida, digite o
        número gerado pelo aplicativo para validar a configuração''')
        return self.value_set('get_qrcode')

    def clean_code(self):
        code = self.cleaned_data['code']
        secret = self.request.user.authcode_set.values_list('secret', flat=True).first()
        print(secret, onetimepass.get_totp(secret))
        if not onetimepass.valid_totp(code, secret):
            raise ValidationError('Código inválido')
        return code

    def submit(self):
        self.request.user.authcode_set.update(active=True)
        self.message()
        return self.redirect()

    def has_permission(self, user):
        return self.request.user.is_authenticated and not self.request.user.authcode_set.filter(active=True).exists()


class Deactivate2fAuthentication(actions.Action):

    class Meta:
        modal = True
        style = 'danger'
        verbose_name = 'Desativar Autentição 2FA'

    def has_permission(self, user):
        return self.request.user.is_authenticated and self.request.user.authcode_set.filter(active=True).exists()

    def submit(self):
        self.request.user.authcode_set.update(active=False)
        self.message()
        self.redirect()


class NotificationSubscribe(actions.ActionView):

    class Meta:
        verbose_name = 'Subscrever para Notificações'

    def has_permission(self, user):
        return True

    def view(self):
        subscription = self.request.POST['subscription']
        if PushNotification.objects.filter(user=self.request.user).exists():
            PushNotification.objects.filter(user=self.request.user).update(subscription=subscription)
        else:
            PushNotification.objects.create(user=self.request.user, subscription=subscription)
        print(subscription)


class ShowIcons(actions.Action):
    class Meta:
        icon = 'palette'
        verbose_name = 'Ícones'

    def view(self):
        libraries = {}
        libraries['Bootstrap'] = bootstrap.ICONS
        if cache.get('materialicons'):
            libraries['Material Icons'] = materialicons.ICONS
        if cache.get('fontawesome'):
            libraries['Font Awesome'] = fontawesome.ICONS
        return dict(settings=settings, libraries=libraries)


class ManageTaskExecution(actions.Action):
    deactivate = actions.BooleanField(label='Desativar', required=False)

    class Meta:
        modal = True
        style = 'danger'
        verbose_name = 'Ativar/Desativar Tarefas Assíncronas'

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.initial['deactivate'] = bool(cache.get('is_tasks_deactivated'))

    def has_permission(self, user):
        return user.is_superuser and not cache.get('is_tasks_deactivated')

    def submit(self):
        deactivate = self.cleaned_data['deactivate']
        cache.set('is_tasks_deactivated', deactivate)
        self.message()
        self.redirect()


class ExecuteQuery(actions.Action):
    query = actions.TextField()

    class Meta:
        icon = 'chat-left-dots'
        verbose_name = 'Executar SQL'
        modal = False
        style = 'primary'

    def submit(self):
        query = self.cleaned_data['query']
        with io.StringIO() as output:
            call_command('query', query, stdout=output, stderr=output)
            return dict(output=output.getvalue())

    def has_permission(self, user):
        return user.is_superuser and user.roles.contains('Remote Developer')


class ExecuteScript(actions.Action):
    script = actions.TextField()

    class Meta:
        icon = 'cast'
        verbose_name = 'Executar Script'
        modal = False
        style = 'primary'

    def submit(self):
        script = self.cleaned_data['script']
        p = subprocess.Popen(
            ['python', 'manage.py', 'shell', '-c', script],
            stdout=subprocess.PIPE, stdin=subprocess.PIPE, stderr=subprocess.PIPE
        )
        stdout, stderr = p.communicate()
        output = '{}{}'.format(stdout.decode(), stderr.decode())
        return dict(output=output)

    def has_permission(self, user):
        return user.is_superuser and user.roles.contains('Remote Developer')


class Signup(actions.ActionView):
    pass1 = actions.CharField(label='Senha', widget=actions.PasswordInput())
    pass2 = actions.CharField(label='Confirmação', widget=actions.PasswordInput())

    class Meta:
        model = User
        verbose_name = 'Cadastrar-se'
        modal = True
        style = 'primary'
        fieldsets = {
            'Dados Pessoais': (('first_name', 'last_name'), 'email'),
            'Dados de Acesso': ('username', ('pass1', 'pass2')),
        }

    def submit(self):
        self.instance.set_password(self.cleaned_data.get('pass1'))
        super().submit()

    def clean(self):
        if User.objects.filter(username=self.cleaned_data.get('username')):
            raise actions.ValidationError('Usuário já cadastrado.')
        if User.objects.filter(email=self.cleaned_data.get('email')):
            raise actions.ValidationError('E-mail já cadastrado.')
        if self.cleaned_data.get('pass1') != self.cleaned_data.get('pass2'):
            raise actions.ValidationError('Senhas não conferem.')
        return self.cleaned_data

    def has_permission(self, user):
        return not user.is_authenticated


class ResetPassword(actions.ActionView):
    email = actions.EmailField(label='E-mail')
    pass1 = actions.CharField(label='Nova Senha', widget=actions.PasswordInput())
    pass2 = actions.CharField(label='Confirmação', widget=actions.PasswordInput())

    class Meta:
        verbose_name = 'Alterar Senha'
        modal = True
        style = 'primary'
        fieldsets = {
            None: ('email', ('pass1', 'pass2'))
        }

    def view(self):
        self.info(
            'Acesse o link que será enviado para seu e-mail para efetivar a alteração de sua senha.'
            '\nVocê tem até 5 minutos para realizar essa confirmação antes que o token expire.'
            '\nCaso não lembre ou não possua e-mail associado ao seu usuário, por favor contacte o administrador.'
        )

    def submit(self):
        self.clear()
        self.info('xxxx')

    def has_permission(self, user):
        return not user.is_authenticated

    def clean(self):
        if not User.objects.filter(email=self.cleaned_data.get('email')).exists():
            raise actions.ValidationError('Usuário não localizado.')
        if self.cleaned_data.get('pass1') != self.cleaned_data.get('pass2'):
            raise actions.ValidationError('Senhas não conferem.')
        return self.cleaned_data


class ExportCsv(actions.Action):
    class Meta:
        icon = 'file-text'
        verbose_name = 'Exportar CSV'
        style = 'primary'

    def view(self):
        return CsvResponse(self.instances.export())

    def has_permission(self, user):
        return self

class ExportXls(actions.Action):
    class Meta:
        icon = 'file-excel'
        verbose_name = 'Exportar XLS'
        style = 'primary'

    def view(self):
        return XlsResponse([([self.instances.model.metaclass().verbose_name_plural, self.instances.export()])])

    def has_permission(self, user):
        return self

class Print(actions.Action):
    class Meta:
        icon = 'printer'
        verbose_name = 'Imprimir'
        style = 'primary'

    def view(self):
        obj = self.instance or self.instances or self.queryset
        return PdfReportResponse(self.request, obj.contextualize(self.request).html(print=True))

    def has_permission(self, user):
        return self


class Workflow(actions.ActionView):
    INITIAL_CONTENT = '''
            <?xml version="1.0" encoding="UTF-8"?>
            <bpmn:definitions xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xmlns:bpmn="http://www.omg.org/spec/BPMN/20100524/MODEL" xmlns:bpmndi="http://www.omg.org/spec/BPMN/20100524/DI" xmlns:dc="http://www.omg.org/spec/DD/20100524/DC" id="Definitions_0nf790r" targetNamespace="http://bpmn.io/schema/bpmn" exporter="bpmn-js (https://demo.bpmn.io)" exporterVersion="12.0.0">
              <bpmn:process id="Process_0rezp77" isExecutable="false">
                <bpmn:startEvent id="StartEvent_0disvw0" />
              </bpmn:process>
              <bpmndi:BPMNDiagram id="BPMNDiagram_1">
                <bpmndi:BPMNPlane id="BPMNPlane_1" bpmnElement="Process_0rezp77">
                  <bpmndi:BPMNShape id="_BPMNShape_StartEvent_2" bpmnElement="StartEvent_0disvw0">
                    <dc:Bounds x="156" y="82" width="36" height="36" />
                  </bpmndi:BPMNShape>
                </bpmndi:BPMNPlane>
              </bpmndi:BPMNDiagram>
            </bpmn:definitions>
        '''

    class Meta:
        icon = 'diagram-3'
        verbose_name = 'Fluxograma'
        modal = False
        style = 'primary'

    def view(self):
        if self.request.POST:
            content = self.request.POST['xml']
            with open('workflow.xml', 'w') as file:
                file.write(self.request.POST['xml'])
            with open('workflow.png', 'wb') as file:
                file.write(base64.b64decode(self.request.POST['png']))
        else:
            if os.path.exists('workflow.xml'):
                with open('workflow.xml') as file:
                    content = file.read()
            else:
                content = Workflow.INITIAL_CONTENT
        return self.render('actions/workflow.html', title='Fluxograma', content=content)

    def has_permission(self, user):
        return user.is_superuser
