# -*- coding: utf-8 -*-
from sloth.decorators import verbose_name, template
from oauth2_provider.models import AbstractApplication
from django.contrib.auth.models import User as DjangoUser
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.db import models


class UserManager(models.Manager):
    def all(self):
        return self.display(
            'username', 'is_superuser', 'get_roles'
        ).actions('LoginAsUser').verbose_name('Usuários')


class User(DjangoUser):

    objects = UserManager()

    class Meta:
        proxy = True
        verbose_name = 'Usuário'
        verbose_name_plural = 'Usuários'
        list_display = 'username',
        fieldsets = {
            'Dados Gerais': (('first_name', 'last_name'), 'username', 'email'),
            'Dados de Acesso': ('is_superuser',)
        }

    def view(self):
        return self.values('get_general_info', 'get_access_info', 'get_roles')

    def get_general_info(self):
        return self.values(('first_name', 'last_name'), 'username', 'email').verbose_name('Dados Gerais')

    def get_access_info(self):
        return self.values('is_superuser',).verbose_name('Dados de Acesso')

    @verbose_name('Papéis')
    def get_roles(self):
        return self.roles.ignore('user').actions('DeleteUserRole')

    def has_role(self, name):
        return self.user.roles.filter(name=name).exists()

    def has_roles(self, name):
        return self.user.roles.filter(name__in=name).exists()


class RoleManager(models.Manager):

    def contains(self, *names):
        return self.filter(name__in=names).exists()


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
    scope = GenericForeignKey('scope_type', 'scope_value')
    scope_key = models.CharField(max_length=50, verbose_name='Escopo', null=True)
    scope_type = models.ForeignKey(ContentType, verbose_name='Tipo do Escopo', null=True, on_delete=models.CASCADE)
    scope_value = models.IntegerField(verbose_name='Valor do Escopo', null=True)

    objects = RoleManager()

    class Meta:
        verbose_name = 'Papel'
        verbose_name_plural = 'Papéis'
        list_display = 'user', 'name', 'scope_key', 'get_scope'
        list_filter = 'user',
        list_per_page = 20

    def __str__(self):
        if self.scope_key and self.scope_value:
            return '{}::{}::{}'.format(
                self.name, self.scope_key, self.scope_value
            )
        else:
            return '{}'.format(self.name)

    def get_scope(self):
        return self.values('scope').verbose_name('Referência')


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
        return self


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

    @template('app/formatters/progress')
    @verbose_name('Progresso')
    def get_progress(self):
        return self.progress

    def get_info(self):
        return self.values(
            ('name', 'user'), ('start', 'end'), 'get_progress', 'message'
        ).refresh(2).actions('StopTask')

    def view(self):
        return self.values('get_info')