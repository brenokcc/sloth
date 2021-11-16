# -*- coding: utf-8 -*-

from oauth2_provider.scopes import BaseScopes

from ..models import Scope


class Scopes(BaseScopes):
    def get_all_scopes(self):
        return {scope.name: scope.description for scope in Scope.objects.all()}

    def get_available_scopes(self, application=None, request=None, *args, **kwargs):
        return list(application.available_scopes.values_list('name', flat=True))

    def get_default_scopes(self, application=None, request=None, *args, **kwargs):
        return list(application.default_scopes.values_list('name', flat=True))
