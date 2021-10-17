# -*- coding: utf-8 -*-

from django.db import models
from oauth2_provider.models import AbstractApplication


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
        return self.accesstoken_set.all()

    def general_data(self):
        return self.values('id', 'name')

    def access_data(self):
        return self.values('client_id', 'client_secret', 'authorization_grant_type')

    def view(self):
        return self.values('general_data', 'access_data', 'default_scopes', 'available_scopes')
