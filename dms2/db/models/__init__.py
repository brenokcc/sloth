import json
from dms2.utils import getattrr, to_action, serialize, to_display, to_filters, to_ordering, to_verbose_name
from django.db import models
from django.db.models import manager


class ValueSet(dict):
    def __init__(self, instance, names, wrap=True, verbose=True):
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
                    value = value.to_dict(name=attr.verbose_name, path=path) if wrap else value.to_list()
                elif isinstance(value, ValueSet):
                    value = dict(
                        type=value.get_type(), name=attr.verbose_name, key=name, actions=[], data=value, path=path
                    ) if wrap else value
                else:
                    value = serialize(value)

                if wrap and hasattr(attr, 'allow'):
                    for form_name in attr.allow:
                        value['actions'].append(
                            to_action(metadata.app_label, form_name, path)
                        )
                if verbose:
                    self[to_verbose_name(type(instance), name)[0]] = value
                else:
                    self[name[4:] if name.startswith('get_') else name] = value
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
            output.update(name=attr.verbose_name)
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


class ModelMixin:

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

    def values(self, *names, wrap=True):
        return ValueSet(self, names, wrap=wrap)

    def view(self):
        return self.values()

    def cached_data(self, data_type):
        attr_name = '_{}_'.format(data_type)
        if hasattr(type(self), attr_name):
            getattr(type(self), attr_name)
        data = []
        for k, v in type(self).__dict__.items():
            if hasattr(v, data_type) and getattr(v, data_type):
                data.append(k)
        setattr(type(self), attr_name, data)
        return data

    def serialize(self, *names):
        data = {}
        primary = self.cached_data('primary')
        if primary:
            data.update(self.values(*primary))
        if names:
            data.update(self.values(*names))
        else:
            data.update(self.view())
        output = dict(type='object', name=str(self), data=data)
        auxiliary = self.cached_data('auxiliary')
        if auxiliary:
            output.update(auxiliary=self.values(*auxiliary))
        return output

    def __str__(self):
        return '{} #{}'.format(self._meta.verbose_name, self.id)
