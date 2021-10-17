# -*- coding: utf-8 -*-

import json

from django.apps import apps
from django.db import models
from django.db.models import manager
from django.forms.models import modelform_factory

from dms2.forms import ModelForm
from dms2.threading import tls
from dms2.utils import getattrr, to_action, serialize, to_display, to_filters, to_ordering, to_verbose_name


class ValueSet(dict):
    def __init__(self, instance, names, wrap=None):
        wrap = getattr(tls, 'wrap', False) if wrap is None else wrap
        self.instance = instance
        self.names = []
        for name in names:
            self.names.extend(name) if isinstance(name, tuple) else self.names.append(name)
        super().__init__()
        if self.names:
            metadata = getattr(self.instance, '_meta')
            for name in self.names:
                attr, value = getattrr(instance, name)
                path = '/{}/{}/{}/{}/'.format(metadata.app_label, metadata.model_name, self.instance.pk, name)
                if isinstance(value, QuerySet):
                    value = value.to_dict(name=getattr(attr, 'verbose_name', name), path=path) if wrap else value.to_list()
                elif isinstance(value, ValueSet):
                    value = dict(
                        type=value.get_type(), name=getattr(attr, 'verbose_name', name), key=name, actions=[], data=value, path=path
                    ) if wrap else value
                else:
                    value = serialize(value)

                if wrap and hasattr(attr, 'allow'):
                    for form_name in attr.allow:
                        value['actions'].append(
                            to_action(metadata.app_label, form_name, path)
                        )
                if wrap:
                    self[to_verbose_name(type(instance), name)[0]] = value
                else:
                    self[name] = value
        else:
            self['id'] = instance.id
            self[type(instance).__name__.lower()] = str(instance)

    def __str__(self):
        return json.dumps(self, indent=4, ensure_ascii=False)

    def get_type(self):
        for value in self.values():
            if isinstance(value, dict) and value.get('type') in ('queryset', 'fieldset'):
                return 'fieldsets'
        return 'fieldset'


class QuerySet(models.QuerySet):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.metadata = dict(
            display=[], filters={}, search=[], ordering=[], paginate=15
        )

    def _clone(self):
        clone = super()._clone()
        clone.metadata = self.metadata
        return clone

    def to_list(self):
        data = []
        for obj in self:
            data.append(obj.values(*self.metadata['display'], wrap=False))
        return data

    def to_dict(self, name=None, path=None, verbose=True):
        if name is None:
            name = str(getattr(self.model, '_meta').verbose_name)
        display = to_display(self.model, self.metadata['display'], verbose)
        filters = to_filters(self.model, self.metadata['filters'], verbose)
        ordering = to_ordering(self.model, self.metadata['ordering'], verbose)
        return dict(
            type='queryset', name=name, count=self.count(), data=self.to_list(),
            metadata=dict(display=display, filters=filters, ordering=ordering),
            actions=[], path=path
        )

    def serialize(self, name=None):
        attr = getattr(self, name or 'all')
        output = self.to_dict()
        metadata = getattr(self.model, '_meta')
        path = '/{}/{}/'.format(metadata.app_label, metadata.model_name)
        if name:
            path = '{}{}/'.format(path, name)
        if hasattr(attr, 'verbose_name'):
            output.update(name=getattr(attr, 'verbose_name', name))
        if hasattr(attr, 'allow'):
            for form_name in attr.allow:
                output['actions'].append(to_action(metadata.app_label, form_name, path))
        output.update(path=path)
        return output

    def display(self, *names):
        self.metadata['display'] = list(names)
        return self

    def search(self, *names):
        self.metadata['search'] = list(names)
        return self

    def filters(self, *names):
        self.metadata['filters'] = list(names)
        return self

    def ordering(self, *names):
        self.metadata['ordering'] = list(names)
        return self

    def paginate(self, size):
        self.metadata['paginate'] = size
        return self


class BaseManager(manager.BaseManager):
    def all(self):
        return self.get_queryset().all()


class Manager(BaseManager.from_queryset(QuerySet)):
    pass


class ModelSerializer(object):

    def __init__(self, instance, *attrs):
        self.instance = instance
        self.attrs = attrs

    def cached_data(self, data_type):
        attr_name = '_{}_'.format(data_type)
        if hasattr(type(self.instance), attr_name):
            getattr(type(self.instance), attr_name)
        data = []
        for k, v in type(self.instance).__dict__.items():
            if hasattr(v, data_type) and getattr(v, data_type):
                data.append(k)
        setattr(type(self.instance), attr_name, data)
        return data

    def serialize(self):
        data = {}
        primary = self.cached_data('primary')
        if primary:
            data.update(self.instance.values(*primary))
        if self.attrs:
            data.update(self.instance.values(*self.attrs))
        else:
            data.update(self.instance.view())
        output = dict(type='object', name=str(self.instance), data=data)
        auxiliary = self.cached_data('auxiliary')
        if auxiliary:
            output.update(auxiliary=self.instance.values(*auxiliary))
        return output


class ModelMixin(object):

    def has_view_permission(self, user):
        return self and user.is_superuser

    def has_attr_view_permission(self, user, name):
        attr = getattr(self, 'has_{}_permission'.format(name), None)
        return attr is None or attr(user)

    def has_add_permission(self, user):
        return self and user.is_superuser

    def has_edit_permission(self, user):
        return self and user.is_superuser

    def has_delete_permission(self, user):
        return self and user.is_superuser

    def values(self, *names, wrap=None):
        return ValueSet(self, names, wrap=wrap)

    def view(self):
        return self.values()

    def serializer(self, *names):
        return ModelSerializer(self, *names)

    def serialize(self, *names):
        return self.serializer(*names).serialize()

    def get_absolute_url(self, prefix=''):
        return '{}/{}/{}/{}/'.format(prefix, self._meta.app_label, self._meta.model_name, self.pk)

    def __str__(self):
        return '{} #{}'.format(self._meta.verbose_name, self.pk)

    @classmethod
    def action_form_cls(cls, action):
        config = apps.get_app_config(cls._meta.app_label)
        forms = __import__(
            '{}.forms'.format(config.module.__package__),
            fromlist=config.module.__package__.split()
        )
        for name in dir(forms):
            if name.lower() == action:
                return getattr(forms, name)
        return None

    @classmethod
    def add_form_cls(cls):
        return modelform_factory(cls, form=ModelForm, exclude=())

    @classmethod
    def edit_form_cls(cls):
        return modelform_factory(cls, form=ModelForm, exclude=())

    @classmethod
    def delete_form_cls(cls):
        return modelform_factory(cls, form=ModelForm, fields=())
