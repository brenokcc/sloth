# -*- coding: utf-8 -*-

from decimal import Decimal
from django.apps import apps
from django.db import models
from django.db.models import *
from django.db.models import base
from django.db.models.query_utils import DeferredAttribute
from sloth.core.queryset import QuerySet
from sloth.core.base import ModelMixin


class GenericModelWrapper(object):
    def __init__(self, obj):
        self._wrapped_obj = obj

    def __getattr__(self, attr):
        if attr == 'prepare_database_save':
            raise AttributeError()
        return getattr(self._wrapped_obj, attr)

    def __str__(self):
        return self._wrapped_obj.__str__()

    def __repr__(self):
        return self._wrapped_obj.__repr__()


class GenericValue(object):
    def __init__(self, value):
        if isinstance(value, str) and '::' in value:
            value_type, value = value.split('::')
            if '.' in value_type:
                value = apps.get_model(value_type).objects.get(pk=value)
            elif value_type == 'str':
                value = value
            elif value_type == 'int':
                value = int(value)
            elif value_type == 'Decimal':
                value = Decimal(value)
            elif value_type == 'float':
                value = float(value)
        self.value = value

    def dumps(self):
        if self.value is not None:
            if isinstance(self.value, GenericModelWrapper):
                return '{}.{}::{}'.format(
                    self.value.metaclass().app_label, self.value.metaclass().model_name, self.value.pk
                )
            return '{}::{}'.format(type(self.value).__name__, self.value)
        return None

class GenericFieldDescriptor(DeferredAttribute):
    def __get__(self, instance, cls=None):
        obj = super().__get__(instance, cls=cls)
        if isinstance(obj.value, Model):
            return GenericModelWrapper(obj.value)
        return obj.value

    def __set__(self, instance, value):
        instance.__dict__[self.field.attname] = GenericValue(value)


class GenericField(CharField):
    descriptor_class = GenericFieldDescriptor

    def __init__(self, *args, max_length=255, null=True, **kwargs):
        super().__init__(*args, max_length=max_length, null=null, **kwargs)

    def get_prep_value(self, value):
        if value is not None:
            if isinstance(value, GenericValue):
                value = value.dumps()
            else:
                value = GenericValue(value).dumps()
        return value


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

    def __init__(self, *args, min=0, max=3, **kwargs):
        self.min = min
        self.max = max
        super().__init__(*args, **kwargs)

    def formfield(self, **kwargs):
        field = super().formfield(**kwargs)
        field.min = self.min
        field.max = self.max
        return field


class DecimalField(models.DecimalField):
    def __init__(self, *args, **kwargs):
        decimal_places = kwargs.pop('decimal_places', 2)
        max_digits = kwargs.pop('max_digits', 9)
        super().__init__(*args, decimal_places=decimal_places, max_digits=max_digits, **kwargs)

    def formfield(self, **kwargs):
        field = super().formfield(**kwargs)
        field.localize = True
        field.widget.is_localized = True
        field.widget.input_type = 'text'
        field.widget.rmask = '#.##0,00'
        return field


class Manager(QuerySet):
    pass


class Model(models.Model, ModelMixin, metaclass=base.ModelBase):

    class Meta:
        abstract = True

    def pre_save(self, *args, **kwargs):
        pass

    def save(self, *args, **kwargs):
        if hasattr(self, '__roles__'):
            setattr(self, '_role_tuples', self.get_role_tuples())
        super().save(*args, **kwargs)

    def post_save(self, *args, **kwargs):
        if hasattr(self, '__roles__'):
            self.sync_roles(getattr(self, '_role_tuples'))

    def delete(self, *args, **kwargs):
        if hasattr(self, '__roles__'):
            print(self.__roles__)
        super().delete(*args, **kwargs)

