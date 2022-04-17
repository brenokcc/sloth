from sloth import actions
from django.contrib import auth


class DeleteUserRole(actions.Action):
    class Meta:
        verbose_name = 'Excluir'
        style = 'danger'

    def submit(self):
        self.instance.delete()
        self.redirect()

class LoginAsUser(actions.Action):
    class Meta:
        verbose_name = 'Acessa como Usuário'
        style = 'warning'

    def submit(self):
        auth.login(self.request, self.instance)
        self.redirect('/')

    def has_permission(self, user):
        return user.is_superuser and self.instance != self.request.user
