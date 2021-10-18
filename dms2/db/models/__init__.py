# -*- coding: utf-8 -*-

import json

from django.apps import apps
from django.db import models
from django.db.models import manager
from django.forms.models import modelform_factory

from dms2.forms import ModelForm
from dms2.utils import getattrr, to_action, serialize, to_display, to_filters, to_ordering, to_verbose_name
from dms2.db.models.decorators import meta


class ValueSet(dict):
    def __init__(self, instance, names):
        self.model = type(instance)
        self.instance = instance
        self.names = []
        for attr_name in names:
            self.names.extend(attr_name) if isinstance(attr_name, tuple) else self.names.append(attr_name)
        super().__init__()

    def loaddata(self, wrap=False, verbose=False):
        if self.names:
            metadata = getattr(self.instance, '_meta')
            for attr_name in self.names:
                attr, value = getattrr(self.instance, attr_name)
                path = '/{}/{}/{}/{}/'.format(metadata.app_label, metadata.model_name, self.instance.pk, attr_name)
                if isinstance(value, QuerySet):
                    verbose_name = getattr(attr, 'verbose_name', attr_name) if verbose else attr_name
                    value = value.serialize(path=path, wrap=wrap, verbose=verbose)
                    if wrap:
                        value['name'] = verbose_name
                elif isinstance(value, ValueSet):
                    key = attr_name
                    verbose_name = getattr(attr, 'verbose_name', attr_name) if verbose else attr_name
                    if attr_name == 'default_fieldset':
                        key = None
                        path = None
                    value.loaddata(wrap=wrap, verbose=verbose)
                    value = dict(
                        type=value.get_type(), name=verbose_name, key=key, actions=[], data=value, path=path
                    ) if wrap else value
                else:
                    value = serialize(value)

                if wrap and hasattr(attr, 'allow'):
                    for form_name in attr.allow:
                        value['actions'].append(
                            to_action(metadata.app_label, form_name, path)
                        )

                if verbose:
                    self[to_verbose_name(self.model, attr_name)[0]] = value
                else:
                    self[attr_name] = value
        else:
            self['id'] = self.instance.id
            self[self.model.__name__.lower()] = str(self.instance)

    def __str__(self):
        return json.dumps(self, indent=4, ensure_ascii=False)

    def get_type(self):
        for value in self.values():
            if isinstance(value, dict) and value.get('type') in ('queryset', 'fieldset'):
                return 'fieldsets'
        return 'fieldset'

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

    def serialize(self, wrap=False, verbose=False):
        self.loaddata(wrap=wrap, verbose=verbose)
        if wrap:
            data = {}
            names = self.cached_data('primary')
            if names:
                extra = self.instance.values(*names)
                extra.loaddata(wrap=wrap, verbose=verbose)
                data.update(extra)
            data.update(self)
            output = dict(type='object', name=str(self.instance), data=data)
            names = self.cached_data('auxiliary')
            if names:
                extra = self.instance.values(*names)
                extra.loaddata(wrap=wrap, verbose=verbose)
                output.update(auxiliary=extra)
            return output
        else:
            if len(self.names) == 1:
                return self[self.names[0]]
            return self


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

    def _get_list_display(self):
        if not self.metadata['display']:
            self.metadata['display'] = [field.name for field in getattr(self.model, '_meta').fields[0:5]]
        return self.metadata['display']

    def _get_list_filter(self):
        return self.metadata['filters']

    def _get_list_ordering(self):
        return self.metadata['ordering']

    def to_list(self):
        data = []
        for obj in self:
            data.append(obj.values(*self._get_list_display()).serialize())
        return data

    def serialize(self, att_name=None, path=None, wrap=False, verbose=True):
        if wrap:
            attr = getattr(self, att_name or 'all')
            if hasattr(attr, 'verbose_name'):
                verbose_name = getattr(attr, 'verbose_name', att_name)
            else:
                verbose_name = str(getattr(self.model, '_meta').verbose_name)
            display = to_display(self.model, self._get_list_display(), verbose)
            filters = to_filters(self.model, self._get_list_filter(), verbose)
            ordering = to_ordering(self.model, self._get_list_ordering(), verbose)
            data = dict(
                type='queryset', name=verbose_name, count=self.count(), actions=[],
                metadata=dict(display=display, filters=filters, ordering=ordering),
                data=self.to_list(), path=path
            )
            metadata = getattr(self.model, '_meta')
            path = '/{}/{}/'.format(metadata.app_label, metadata.model_name)
            if att_name:
                path = '{}{}/'.format(path, att_name)

            if 'actions' in data and hasattr(attr, 'allow'):
                for form_name in attr.allow:
                    data['actions'].append(to_action(metadata.app_label, form_name, path))
                data.update(path=path)
            return data
        return self.to_list()

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
    def get_queryset(self):
        return super().get_queryset().all()


class Manager(BaseManager.from_queryset(QuerySet)):
    pass


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

    def values(self, *names):
        if not names:
            names = 'default_fieldset',
        return ValueSet(self, names)

    @meta('Dados Gerais')
    def default_fieldset(self):
        model = type(self)
        names = [field.name for field in getattr(model, '_meta').fields[0:5]]
        return self.values(*names)

    def view(self):
        return self.values()

    def serialize(self, name=None, wrap=False, verbose=False):
        return (self.values(name) if name else self.values()).serialize(wrap=wrap, verbose=verbose)

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
