from django.db import models
from django.db.models import manager, Model
from django.db.models.base import ModelBase

from .base import ModelMixin
from .query import QuerySet


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

    if bases == (Model,):
        bases = Model, ModelMixin
    cls = ___new___(mcs, name, bases, attrs, **kwargs)
    return cls


ModelBase.__new__ = __new__
models.QuerySet = QuerySet
models.Manager = Manager


