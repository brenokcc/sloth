from sloth import actions
from django.contrib import auth
from django.conf import settings


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

    class Meta:
        verbose_name = None
        ajax = False
        submit_label = 'Acessar'
        fieldsets = {
            None: ('username', 'password')
        }

    def __init__(self, *args, **kwargs):
        self.user = None
        super().__init__(*args, **kwargs)
        if settings.SLOTH['LOGIN'].get('USERNAME_MASK'):
            self.fields['username'].widget.mask = settings.SLOTH['LOGIN']['USERNAME_MASK']

    def clean(self):
        if self.cleaned_data:
            username = self.cleaned_data.get('username')
            password = self.cleaned_data.get('password')
            if username and password:
                self.user = auth.authenticate(
                    self.request, username=username, password=password
                )
                if self.user is None:
                    raise actions.ValidationError('Login e senha não conferem.')
        return self.cleaned_data

    def submit(self):
        if self.user:
            auth.login(self.request, self.user, backend='django.contrib.auth.backends.ModelBackend')


class ChangePassword(actions.Action):
    password = actions.CharField(label='Senha', widget=actions.PasswordInput())
    password2 = actions.CharField(label='Confirmação', widget=actions.PasswordInput())

    class Meta:
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