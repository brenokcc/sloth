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


class Login(actions.Action):
    username = actions.CharField(label='Login')
    password = actions.CharField(label='Senha', widget=actions.PasswordInput())
    auth_code = actions.CharField(label='Código', widget=actions.PasswordInput(), required=False)

    class Meta:
        verbose_name = settings.SLOTH['LOGIN']['TITLE']
        ajax = False
        submit_label = 'Acessar'
        fieldsets = {
            None: ('username', 'password', 'auth_code'),
        }

    def __init__(self, *args, **kwargs):
        self.user = None
        super().__init__(*args, **kwargs)
        if settings.SLOTH['LOGIN'].get('USERNAME_MASK'):
            self.fields['username'].widget.mask = settings.SLOTH['LOGIN']['USERNAME_MASK']
        self.show('auth_code') if self.requires_2fa() else self.hide('auth_code')

    def view(self):
        if 'o' in self.request.GET:
            provider = settings.SLOTH['OAUTH_LOGIN'][self.request.GET['o'].upper()]
            authorize_url = '{}?response_type=code&client_id={}&redirect_uri={}'.format(
                provider['AUTHORIZE_URL'], provider['CLIENTE_ID'], provider['REDIRECT_URI']
            )
            if provider.get('SCOPE'):
                authorize_url = '{}&scope={}'.format(authorize_url, provider.get('SCOPE'))
            self.request.session['o'] = self.request.GET['o']
            self.request.session.save()
            self.redirect(authorize_url)
        elif 'code' in self.request.GET:
            provider = settings.SLOTH['OAUTH_LOGIN'][self.request.session['o'].upper()]
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
                    self.alert('Usuário "{}" inexistente.'.format(username))
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


class ChangePassword(actions.Action):
    password = actions.CharField(label='Senha', widget=actions.PasswordInput())
    password2 = actions.CharField(label='Confirmação', widget=actions.PasswordInput())

    class Meta:
        modal = True
        verbose_name = 'Alterar Senha'

    def clean(self):
        password = self.cleaned_data.get('password')
        password2 = self.cleaned_data.get('password2')
        if password != password2:
            raise actions.ValidationError('Senhas não conferem.')

        if settings.SLOTH.get('FORCE_PASSWORD_DEFINITION') == True and settings.SLOTH.get('DEFAULT_PASSWORD'):
            default_password = settings.SLOTH['DEFAULT_PASSWORD'](self.request.user)
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
        return user.is_authenticated


class Logout(actions.Action):
    class Meta:
        verbose_name = 'Sair'
        ajax = False

    def view(self):
        self.request.session.clear()
        auth.logout(self.request)
        self.redirect('/')


class Activate2FAuthentication(actions.Action):
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


class Deactivate2FAuthentication(actions.Action):

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


class NotificationSubscribe(actions.Action):

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


class Icons(actions.Action):

    def view(self):
        libraries = {}
        libraries['Bootstrap'] = bootstrap.ICONS
        if 'materialicons' in settings.SLOTH.get('ICONS', ()):
            libraries['Material Icons'] = materialicons.ICONS
        if 'fontawesome' in settings.SLOTH.get('ICONS', ()):
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
