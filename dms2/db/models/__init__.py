# -*- coding: utf-8 -*-
import six
from django.db import models
from django.db.models import *
from django.db.models import base
from django.db.models import options

from .decorators import meta
from ...query import QuerySet

setattr(options, 'DEFAULT_NAMES', options.DEFAULT_NAMES + (
    'icon', 'list_display', 'search_fields', 'list_per_page', 'list_filter', 'fieldsets'
))


class CharField(CharField):
    def __init__(self, *args, max_length=255, **kwargs):
        self.mask = kwargs.pop('mask', None)
        self.rmask = kwargs.pop('rmask', None)
        super().__init__(*args, max_length=max_length, **kwargs)

    def formfield(self, **kwargs):
        field = super().formfield(**kwargs)
        field.widget.mask = self.mask
        field.widget.rmask = self.rmask
        return field


class ForeignKey(ForeignKey):
    def __init__(self, to, on_delete=CASCADE, **kwargs):
        super().__init__(to=to, on_delete=on_delete, **kwargs)


class OneToOneField(OneToOneField):
    def __init__(self, to, on_delete=SET_NULL, **kwargs):
        if kwargs.get('blank'):
            kwargs.update(null=True)
        super().__init__(to=to, on_delete=on_delete, **kwargs)


class OneToManyField(ManyToManyField):
    one_to_many = True


class Manager(QuerySet):
    pass


class Model(six.with_metaclass(base.ModelBase, models.Model)):

    class Meta:
        abstract = True

    def save(self, *args, **kwargs):
        if hasattr(self, '_roles'):
            tuples = self.get_role_tuples()
            super().save(*args, **kwargs)
            self.sync_roles(tuples)
        else:
            super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        if hasattr(self, '_roles'):
            print(self._roles)
        super().delete(*args, **kwargs)

