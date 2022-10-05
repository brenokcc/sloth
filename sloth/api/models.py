# -*- coding: utf-8 -*-
from django.apps import apps
from oauth2_provider.models import AbstractApplication
from django.contrib.auth.models import User as DjangoUser
from sloth.db import models, meta


def user_post_save(instance, created, **kwargs):
    pass


models.signals.post_save.connect(user_post_save, sender=DjangoUser)


class UserManager(models.Manager):
    def all(self):
        return self.display(
            'username', 'is_superuser', 'get_roles_names'
        ).actions('LoginAsUser').verbose_name('Usuários').attach(
            'active', 'inactive'
        )


    def active(self):
        return self.all().filter(is_active=True).verbose_name('Ativos')


    def inactive(self):
        return self.all().filter(is_active=False).verbose_name('Inativos')


class User(DjangoUser):

    objects = UserManager()

    class Meta:
        proxy = True
        verbose_name = 'Usuário'
        verbose_name_plural = 'Usuários'
        fieldsets = {
            'Dados Gerais': (('first_name', 'last_name'), 'username', 'email'),
            'Dados de Acesso': (('is_superuser', 'is_staff', 'is_active'),)
        }

    def view(self):
        return self.values('get_general_info', 'get_access_info', 'get_roles')

    def get_general_info(self):
        return self.values(('first_name', 'last_name'), 'username', 'email').verbose_name('Dados Gerais')

    def get_access_info(self):
        return self.values('is_superuser',).verbose_name('Dados de Acesso')

    @meta('Papéis')
    def get_roles(self):
        return self.roles.all().ignore('user')

    @meta('Papéis')
    def get_roles_names(self):
        return list(self.roles.values_list('name', flat=True).distinct())

    def save(self, *args, **kwargs):
        created = self.pk is None
        super().save(*args, **kwargs)
        user_post_save(self, created=created)


class RoleManager(models.Manager):

    def all(self):
        return self.display(
            'user', 'name', 'active', 'scope_key', 'get_scope_value'
        ).actions(
            'ActivateUserRole', 'DeactivateUserRole', 'Delete'
        ).limit_per_page(20)

    def active(self):
        return self.filter(active=True)

    def inactive(self):
        return self.filter(active=False)

    def contains(self, *names):
        if 'instance' in self._hints:
            if not hasattr(self._hints['instance'], '_cached_role_names'):
                self._hints['instance']._cached_role_names = self.filter(active=True).values_list('name', flat=True)
            for name in names:
                if name in self._hints['instance']._cached_role_names:
                    return True
            return False
        return self.filter(active=True, name__in=names).exists()

    def names(self):
        return self.values_list('name', flat=True).distinct()


class AuthCode(models.Model):
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        verbose_name='Usuário'
    )
    secret = models.CharField(max_length=16, verbose_name='Chave')
    active = models.BooleanField(verbose_name='Ativo', default=False)

    class Meta:
        verbose_name = 'Código de Autenticação'
        verbose_name_plural = 'Códigos de Autenticação'

    def __str__(self):
        return self.secret


class Role(models.Model):
    user = models.ForeignKey(
        User,
        related_name='roles',
        null=True,
        blank=True,
        on_delete=models.CASCADE,
        verbose_name='Usuário'
    )
    name = models.CharField(max_length=50, verbose_name='Nome')
    scope_key = models.CharField(max_length=50, verbose_name='Escopo', null=True, blank=True)
    scope_type = models.CharField(max_length=50, verbose_name='Tipo do Escopo', null=True, db_index=True, blank=True)
    scope_value = models.IntegerField(verbose_name='Valor do Escopo', null=True, db_index=True, blank=True)
    active = models.BooleanField(verbose_name='Ativo', default=True, blank=True)

    objects = RoleManager()

    class Meta:
        verbose_name = 'Papel'
        verbose_name_plural = 'Papéis'

    def __str__(self):
        if self.scope_key and self.scope_value:
            return '{}::{}::{}'.format(
                self.name, self.scope_key, self.scope_value
            )
        else:
            return '{}'.format(self.name)

    @meta('Referência')
    def get_scope_value(self):
        if self.scope_type:
            return apps.get_model(self.scope_type).objects.filter(pk=self.scope_value).first()


class Scope(models.Model):
    name = models.CharField(max_length=50, verbose_name='Nome')
    description = models.TextField(verbose_name='Descrição')

    class Meta:
        verbose_name = 'Escopo'
        verbose_name_plural = 'Escopos'

    def __str__(self):
        return self.name


class Application(AbstractApplication):
    default_scopes = models.ManyToManyField(Scope, related_name='s2', blank=True)
    available_scopes = models.ManyToManyField(Scope, related_name='s1', blank=True)

    class Meta:
        verbose_name = 'Aplicação'
        verbose_name_plural = 'Aplicações'

    def __str__(self):
        return self.name

    def get_access_tokens(self):
        return self.accesstoken_set.all().verbose_name('Tokens de Acesso')

    def general_data(self):
        return self.values('id', 'name').verbose_name('Dados Gerais')

    def access_data(self):
        return self.values('client_id', 'client_secret', 'authorization_grant_type').verbose_name('Dados de Acesso')

    def view(self):
        return self.values('general_data', 'access_data', 'default_scopes', 'available_scopes')


class TaskManager(models.Manager):
    def all(self):
        return self.display('id', 'user', 'name', 'start', 'end', 'get_progress')


class Task(models.Model):
    STOPPED_TASKS = []

    user = models.ForeignKey(User, verbose_name='Usuário', on_delete=models.CASCADE)

    name = models.CharField(verbose_name='Nome', max_length=255)
    start = models.DateTimeField(verbose_name='Início', auto_now=True)
    end = models.DateTimeField(verbose_name='Fim', null=True)

    progress = models.IntegerField(verbose_name='Progresso', default=0)
    message = models.CharField(verbose_name='Mensagem', null=True, max_length=255)
    stopped = models.BooleanField(verbose_name='Interrompida', default=False)
    error = models.TextField(verbose_name='Erro', null=True)

    objects = TaskManager()

    class Meta:
        verbose_name = 'Tarefa'
        verbose_name_plural = 'Tarefas'

    def __str__(self):
        return 'Tarefa {}'.format(self.pk)

    def stop(self):
        self.stopped = True
        self.save()

    @meta('Mensagem', 'messages/message')
    def get_message(self):
        if self.error:
            return 'danger', self.error
        elif self.stopped:
            return 'warning', 'Interrompida pelo usuário'
        elif self.progress < 100:
            return 'primary', 'Em execução'
        else:
            return 'success', self.message or 'Concluída'

    @meta('Progresso', renderer='utils/progress')
    def get_progress(self):
        return self.progress

    def get_info(self):
        return self.values(
            ('name', 'user'), ('start', 'end'), 'get_progress', 'get_message'
        ).reload(seconds=5, condition='in_progress', max_requests=120).actions('StopTask')

    def in_progress(self):
        return self.end is None

    def view(self):
        return self.values('get_info')

    def has_view_permission(self, user):
        return user.is_superuser or self.user == user


class PushNotification(models.Model):
    user = models.OneToOneField(DjangoUser, verbose_name='Usuário', on_delete=models.CASCADE, related_name='push_notification')
    subscription = models.JSONField(verbose_name='Dados da Inscrição')
