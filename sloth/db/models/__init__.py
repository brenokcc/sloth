# -*- coding: utf-8 -*-
import datetime
import json
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

    def __setattr__(self, attr, value):
        if attr == '_wrapped_obj':
            super().__setattr__(attr, value)
        elif self._wrapped_obj is not None:
            self._wrapped_obj.__setattr__(attr, value._wrapped_obj)

    def __str__(self):
        return self._wrapped_obj.__str__()

    def __repr__(self):
        return self._wrapped_obj.__repr__()


class GenericValue(object):
    def __init__(self, value):
        self.value = value

    def get_value(self):
        if isinstance(self.value, str) and '::' in self.value:
            value_type, value = self.value.split('::')
            if '.' in value_type:
                self.value = apps.get_model(value_type).objects.get(pk=value)
            elif value_type == 'str':
                self.value = value
            elif value_type == 'int':
                self.value = int(value)
            elif value_type == 'Decimal':
                self.value = Decimal(value)
            elif value_type in ('date', 'datetime'):
                self.value = datetime.datetime.strptime(value[0:10], '%Y-%m-%d')
            elif value_type == 'float':
                self.value = float(value)
            elif value_type == 'bool':
                self.value = value == 'True'
            elif value_type == 'list':
                self.value = json.loads(value)
        return self.value

    def dumps(self):
        value = self.value
        if value is not None:
            if isinstance(value, Model):
                value = GenericModelWrapper(value)
            if isinstance(value, GenericModelWrapper):
                return '{}.{}::{}'.format(
                    value.metaclass().app_label, value.metaclass().model_name, value.pk
                )
            if hasattr(value, 'model'):
                value = list(value.values_list('pk', flat=True))
            if isinstance(value, list):
                value = json.dumps(value)
            return '{}::{}'.format(type(value).__name__, value)
        return None


class GenericFieldDescriptor(DeferredAttribute):
    def __get__(self, instance, cls=None):
        obj = super().__get__(instance, cls=cls)
        if isinstance(obj.value, Model):
            return GenericModelWrapper(obj.value)
        return obj.get_value()

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


class ColorField(CharField):
    def __init__(self, *args, max_length=7, **kwargs):
        super().__init__(*args, max_length=max_length, **kwargs)

    def formfield(self, **kwargs):
        from sloth.actions.inputs import ColorInput
        field = super().formfield(**kwargs)
        field.widget = ColorInput()
        return field


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


class BrCepField(CharField):
    def __init__(self, *args, **kwargs):
        kwargs.update(mask='00.000-000')
        super().__init__(*args, **kwargs)


class BrCpfField(CharField):
    def __init__(self, *args, **kwargs):
        kwargs.update(mask='000.000.000-00')
        super().__init__(*args, **kwargs)


class BrCnpjField(CharField):
    def __init__(self, *args, **kwargs):
        kwargs.update(mask='00.000.000/0000-00')
        super().__init__(*args, **kwargs)


class BrCarPlateField(CharField):
    def __init__(self, *args, **kwargs):
        kwargs.update(mask='AAA-0A00')
        super().__init__(*args, **kwargs)


class BrPhoneField(CharField):
    def __init__(self, *args, **kwargs):
        kwargs.update(mask='0000-0000')
        super().__init__(*args, **kwargs)


class BrRegionalPhoneField(CharField):
    def __init__(self, *args, **kwargs):
        kwargs.update(mask='(00) 00000-0000')
        super().__init__(*args, **kwargs)


class TextField(TextField):
    def __init__(self, *args, formatted=False, **kwargs):
        self.formatted = formatted
        super().__init__(*args, **kwargs)

    def formfield(self, **kwargs):
        field = super().formfield(**kwargs)
        field.widget.formatted = self.formatted
        return field


class ForeignKey(ForeignKey):
    def __init__(self, to, on_delete=CASCADE, **kwargs):
        self.picker = kwargs.pop('picker', None)
        self.auto_user = kwargs.pop('auto_user', False)
        super().__init__(to=to, on_delete=on_delete, **kwargs)

    def formfield(self, **kwargs):
        field = super().formfield(**kwargs)
        if self.picker:
            field.picker = self.picker
        if self.auto_user:
            field.auto_user = self.auto_user
        return field


class CurrentUserField(ForeignKey):
    def __init__(self, *args, **kwargs):
        kwargs.update(to='auth.User')
        super().__init__(*args, **kwargs)


class ManyToManyField(ManyToManyField):
    def __init__(self, *args, **kwargs):
        self.picker = kwargs.pop('picker', None)
        super().__init__(*args, **kwargs)

    def formfield(self, **kwargs):
        field = super().formfield(**kwargs)
        if self.picker:
            field.picker = self.picker
        return field


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


class Decimal3Field(models.DecimalField):
    def __init__(self, *args, **kwargs):
        decimal_places = kwargs.pop('decimal_places', 3)
        max_digits = kwargs.pop('max_digits', 9)
        super().__init__(*args, decimal_places=decimal_places, max_digits=max_digits, **kwargs)


class Manager(QuerySet):
    pass


class Model(models.Model, ModelMixin, metaclass=base.ModelBase):

    class Meta:
        abstract = True

    def pre_save(self, *args, **kwargs):
        setattr(self, '_pre_saved', True)
        if hasattr(self, '__roles__'):
            setattr(self, '_role_tuples', self.get_role_tuples(True))

    def save(self, *args, **kwargs):
        pre_saved = getattr(self, '_pre_saved', False)
        if pre_saved is False:
            self.pre_save()

        super().save(*args, **kwargs)

        if pre_saved is False:
            self.post_save()

    def post_save(self, *args, **kwargs):
        if hasattr(self, '__roles__') and hasattr(self, '_role_tuples'):
            self.sync_roles(getattr(self, '_role_tuples'))

    def persist(self):
        self.pre_save()
        self.save()
        self.post_save()

    def delete(self, *args, **kwargs):
        if hasattr(self, '__roles__'):
            setattr(self, '_role_tuples', self.get_role_tuples(True))
        super().delete(*args, **kwargs)
        if hasattr(self, '__roles__') and hasattr(self, '_role_tuples'):
            self.sync_roles(getattr(self, '_role_tuples'))

    def __str__(self):
        for field in self.metaclass().fields:
            if isinstance(field, models.CharField):
                return getattr(self, field.name)
        return '{} #{}'.format(self.metaclass().verbose_name, self.pk)