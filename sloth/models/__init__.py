# -*- coding: utf-8 -*-

from django.contrib.auth.models import User as DjangoUser
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.db import models
from sloth.db import meta


class UserManager(models.Manager):
    @meta('Usuários')
    def all(self):
        return super().all().list_display('username', 'is_superuser', 'get_roles')


class User(DjangoUser):

    objects = UserManager()

    class Meta:
        proxy = True
        verbose_name = 'Usuário'
        verbose_name_plural = 'Usuários'
        list_display = 'username',
        fieldsets = {
            'Dados Gerais': (('first_name', 'last_name'), 'username', 'email'),
            'Dados de Acesso': ('is_superuser')
        }

    def view(self):
        return self.values('get_general_info', 'get_access_info')

    @meta('Dados Gerais')
    def get_general_info(self):
        return self.values(('first_name', 'last_name'), 'username', 'email')

    @meta('Dados de Acesso')
    def get_access_info(self):
        return self.values('is_superuser',)

    @meta('Papeis')
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

    @meta('Referência')
    def get_scope(self):
        return self.scope
