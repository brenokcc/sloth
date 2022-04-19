from django.db import models
from django.db.models import options
from django.db.models import manager
from django.db.models.base import ModelBase

from sloth.core.base import ModelMixin
from sloth.core.query import QuerySet


PROXIED_MODELS = []


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
    'icon', 'list_display', 'search_fields', 'list_per_page', 'list_filter', 'fieldsets',
    'list_template', 'view_template', 'select_template', 'select_fields'
))



