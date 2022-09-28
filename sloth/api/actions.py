import os
import onetimepass
import base64

from django.core.exceptions import ValidationError

from sloth import actions, meta
from django.contrib import auth
from django.conf import settings
from .models import AuthCode


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
        type(self.instance).STOPPED_TASKS.append(self.instance.id)
        self.redirect(message='Ação realizada com sucesso')

    def has_permission(self, user):
        return self.instance.in_progress() and (user.is_superuser or self.instance.user == user)

class Login(actions.Action):
    username = actions.CharField(label='Login')
    password = actions.CharField(label='Senha', widget=actions.PasswordInput())
    auth_code = actions.CharField(label='Código', widget=actions.PasswordInput(), required=False)

    class Meta:
        verbose_name = None
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
        self.hide('auth_code')

    def on_username_change(self, username):
        if settings.SLOTH.get('2FA', False) and AuthCode.objects.filter(user__username=username, active=True).exists():
            self.show('auth_code')
        else:
            self.hide('auth_code')

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
            if self.user and self.user.authcode_set.filter(active=True).exists():
                user_auth_code = self.user.authcode_set.values_list('secret', flat=True).first()
                if settings.SLOTH.get('2FA', False) and not onetimepass.valid_totp(auth_code, user_auth_code):
                    raise actions.ValidationError('Código de autenticação inválido.')
        return self.cleaned_data

    def submit(self):
        if self.user:
            auth.login(self.request, self.user, backend='django.contrib.auth.backends.ModelBackend')


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
        self.redirect('..', message='Senha alterada com sucesso.')

    def has_permission(self, user):
        return user.is_authenticated


class Activate2FAuthentication(actions.Action):
    code = actions.CharField(label='Código')

    class Meta:
        modal = True
        verbose_name = 'Ativar Autentição 2FA'

    def has_permission(self, user):
        return settings.SLOTH.get('2FA', False) \
               and not self.request.user.authcode_set.filter(active=True).exists()

    @meta('QrCode', renderer='qrcode')
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

    def display(self):
        return self.values('get_qrcode')

    def get_instructions(self):
        return '''Para ativar a autenticação de dois fatores,
        baixe o aplicativo (Google Authenticator, Duo Mobile, etc)
        e escaneio o QrCode exibido na tela. Em seguida, digite o
        número gerado pelo aplicativo para validar a configuração'''

    def clean_code(self):
        code = self.cleaned_data['code']
        secret = self.request.user.authcode_set.values_list('secret', flat=True).first()
        print(secret, onetimepass.get_totp(secret))
        if not onetimepass.valid_totp(code, secret):
            raise ValidationError('Código inválido')
        return code

    def submit(self):
        self.request.user.authcode_set.update(active=True)
        return self.redirect('..', 'Ativação realizada com sucesso.')


class Deactivate2FAuthentication(actions.Action):

    class Meta:
        modal = True
        style = 'danger'
        verbose_name = 'Desativar Autentição 2FA'

    def has_permission(self, user):
        return settings.SLOTH.get('2FA', False) \
               and self.request.user.authcode_set.filter(active=True).exists()

    def submit(self):
        self.request.user.authcode_set.update(active=False)
        return self.redirect('..', 'Desativação realizada com sucesso.')