# -*- coding: utf-8 -*-
from sloth.db import verbose_name
from oauth2_provider.models import AbstractApplication
from django.contrib.auth.models import User as DjangoUser
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.db import models


class UserManager(models.Manager):
    def all(self):
        return super().all().list_display('username', 'is_superuser', 'get_roles').verbose_name('Usuários')


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
        return self.values('get_general_info', 'get_access_info')

    def get_general_info(self):
        return self.values(('first_name', 'last_name'), 'username', 'email').verbose_name('Dados Gerais')

    def get_access_info(self):
        return self.values('is_superuser',).verbose_name('Dados de Acesso')

    @verbose_name('Papéis')
    def get_roles(self):
        return [role.name for role in self.roles.all()]

    def has_role(self, name):
        return self.user.roles.filter(name=name).exists()

    def has_roles(self, name):
        return self.user.roles.filter(name__in=name).exists()


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

    class Meta:
        verbose_name = 'Papel'
        verbose_name_plural = 'Papéis'
        list_display = 'user', 'name', 'scope_key', 'get_scope'
        list_filter = 'user',
        list_per_page = 20

    def __str__(self):
        if self.scope_key and self.scope_value:
            return '{}:{}:{}:{}'.format(
                self.name, self.user.get_username(), self.scope_key, self.scope_value
            )
        else:
            return '{}:{}'.format(self.name, self.user.get_username())

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
