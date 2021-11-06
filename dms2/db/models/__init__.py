# -*- coding: utf-8 -*-
import six
from django.contrib.contenttypes.models import ContentType
from django.db import models
from django.db.models import *
from django.db.models import base
from django.db.models import options

from .decorators import meta
from ...query import QuerySet
from ...utils import getattrr

setattr(options, 'DEFAULT_NAMES', options.DEFAULT_NAMES + (
    'icon', 'display', 'search', 'limit', 'filters', 'fieldsets'
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
        from ...models import Role
        if hasattr(self, '_roles'):
            for role in self._roles:
                user = getattrr(self, role['user'])[1]
                pks = []
                if hasattr(user, 'all'):
                    for pk in user:
                        pks.append(pk)
                else:
                    pks.append(user.pk)
                for pk in pks:
                    Role.objects.get_or_create(
                        user_id=pk, name=role['name'], scope_type=None, scope_key=None, scope_value=None
                    )
                    for scope_key, scope_value in role['scopes'].items():
                        value = self if scope_value in ('pk', 'self') else getattrr(self, scope_value)[1]
                        if value:
                            scope_type = ContentType.objects.get_for_model(type(value))
                            Role.objects.get_or_create(
                                user_id=pk, name=role['name'], scope_type=scope_type,
                                scope_key=scope_key, scope_value=value.pk
                            )
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        if hasattr(self, '_roles'):
            print(self._roles)
        super().delete(*args, **kwargs)

