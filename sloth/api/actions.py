from sloth import actions
from django.contrib import auth

from sloth.api.models import User


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
        verbose_name = 'Acessa como Usuário'
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
        return self.instance.end is None and self.instance.user == user
