
from django.apps import apps
from django.conf import settings
from django.db import models
from django.db.models import options
from django.db.models import manager
from django.db.models.base import ModelBase

from sloth.core.base import ModelMixin
from sloth.core.queryset import QuerySet
from sloth.core.validation import validate_model

# import os
# import zipfile
# file_name = os.path.join(os.path.dirname(__file__), 'app', 'static', 'icons', 'fontawesome', 'fontawesome.min.js')
# if not os.path.exists(file_name):
#     with zipfile.ZipFile('{}.zip'.format(file_name), 'r') as file:
#         file.extractall(os.path.dirname(file_name))

PROXIED_MODELS = []

class RoleLookup:
    def __init__(self, instance):
        self.instance = instance
        self.lookups = []

    def role_lookups(self, *names, **scopes):
        self.lookups.append((names, scopes))
        return self

    def _apply(self, user):
        qs = type(self.instance).objects.filter(pk=self.instance.pk)
        for names, scopes in self.lookups:
            qs.role_lookups(*names, **scopes)
        return qs.apply_role_lookups(user)

    def apply(self, user):
        for names, scopes in self.lookups:
            for role in user.roles.all():
                if role.name in names:
                    if scopes:
                        for scope_value_attr, scope_key in scopes.items():
                            if role.scope_key == scope_key:
                                scope_value = getattr(self.instance, scope_value_attr)
                                scope_value = scope_value if type(scope_value) == int else scope_value.pk
                                if role.scope_value == scope_value:
                                    return True
                    else:
                        return True
        return False

def meta(verbose_name=None, renderer=None, **metadata):
    def decorate(func):
        if verbose_name:
            setattr(func, '__verbose_name__', verbose_name)
        if renderer:
            setattr(func, '__template__', renderer)
        if metadata:
            setattr(func, '__metadata__', metadata)

        return func
    return decorate


def initilize():
    for module in ('dashboard', 'actions'):
        for app_label in settings.INSTALLED_APPS:
            try:
                __import__('{}.{}'.format(app_label, module), fromlist=app_label.split('.'))
                # print('{} {} initilized!'.format(app_label, module))
            except ImportError as e:
                if not e.name.endswith('dashboard') and not e.name.endswith('actions'):
                    raise e
            except BaseException as e:
                raise e
    for model in apps.get_models():
        validate_model(model)


class BaseManager(manager.BaseManager):
    def get_queryset(self):
        return super().get_queryset()

    def all(self):
        return self.get_queryset().all()


class Manager(BaseManager.from_queryset(QuerySet)):
    pass


___new___ = ModelBase.__new__


def __new__(mcs, name, bases, attrs, **kwargs):

    if attrs['__module__'] != '__fake__':
        # See .db.models.Manager
        if 'objects' in attrs and isinstance(attrs['objects'], QuerySet):
            queryset_class = attrs['objects']
            attrs.update(objects=BaseManager.from_queryset(type(queryset_class))())
        # Defining the objects Manager using .db.models.QuerySet
        if 'objects' not in attrs and not all(['objects' in dir(cls) for cls in bases]):
            attrs.update(objects=BaseManager.from_queryset(QuerySet)())

    if ModelMixin not in bases:
        bases = bases + (ModelMixin, )
    cls = ___new___(mcs, name, bases, attrs, **kwargs)
    if cls._meta.proxy_for_model:
        PROXIED_MODELS.append(cls._meta.proxy_for_model)
    return cls


ModelBase.__new__ = __new__
models.QuerySet = QuerySet
models.Manager = Manager

setattr(options, 'DEFAULT_NAMES', options.DEFAULT_NAMES + (
    'icon', 'fieldsets', 'select_template', 'select_fields', 'search_fields'
))



