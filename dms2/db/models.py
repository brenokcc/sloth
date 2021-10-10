import json
from dms2.utils import getattrr
from django.db.models import *
from django.db.models import base, manager


class CharField(CharField):
    def __init__(self, *args, **kwargs):
        kwargs.setdefault('max_length', 255)
        super().__init__(*args, **kwargs)


class ForeignKey(ForeignKey):
    def __init__(self, *args, **kwargs):
        kwargs.setdefault('on_delete', CASCADE)
        super().__init__(*args, **kwargs)


class OneToOneField(OneToOneField):
    def __init__(self, *args, **kwargs):
        kwargs.setdefault('on_delete', CASCADE)
        super().__init__(*args, **kwargs)


class ValueSet(dict):
    def __init__(self, instance, names):
        self.instance = instance
        self.names = []
        for name in names:
            self.names.extend(name) if isinstance(name, tuple) else self.names.append(name)
        super().__init__()
        if self.names:
            metadata = getattr(self.instance, '_meta')
            for name in self.names:
                verbose_name, value = getattrr(instance, name)
                path = '/{}/{}/{}/{}/'.format(metadata.app_label, metadata.model_name, self.instance.pk, name)
                if hasattr(value, 'pk'):
                    value = str(value)
                if hasattr(value, 'all'):
                    value = value.to_dict(verbose_name, path=path)
                if isinstance(value, ValueSet):
                    value = dict(name=verbose_name, type=value.get_type(), data=value, path=path)
                if name.startswith('get_'):
                    name = name[4:]
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


class QuerySet(QuerySet):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.metadata = dict(
            search=[], display=['id', self.model.__name__.lower()], filters=[], paginate=15
        )

    def _clone(self):
        clone = super()._clone()
        clone.metadata = self.metadata
        return clone

    def to_dict(self, name=None, **kwargs):
        data = []
        for obj in self:
            data.append(obj.values())
        return dict(name=name, type='queryset', data=data, metadata=self.metadata, **kwargs)

    def serialize(self, name=None):
        attr = getattr(self, name or 'all')
        output = self.to_dict()
        metadata = getattr(self.model, '_meta')
        path = '/{}/{}/'.format(metadata.app_label, metadata.model_name)
        if name:
            path = '{}{}/'.format(path, name)
        if hasattr(attr, 'verbose_name'):
            output.update(name=attr.verbose_name)
        output.update(path=path)
        return output

    def search(self, *names):
        self.metadata['search'] = list(names)
        return self

    def display(self, *names):
        self.metadata['display'] = list(names)
        return self

    def filters(self, *names):
        self.metadata['filters'] = list(names)
        return self

    def paginate(self, size):
        self.metadata['paginate'] = size
        return self


class ModelBase(base.ModelBase):
    def __new__(mcs, name, bases, attrs):
        fromlist = list(map(str, attrs['__module__'].split('.')))
        module = __import__(attrs['__module__'], fromlist=fromlist)
        if hasattr(module, '{}Set'.format(name)):
            queryset_class = getattr(module, '{}Set'.format(name))
            attrs.update(objects=manager.BaseManager.from_queryset(queryset_class)())
        if 'objects' not in attrs:
            attrs.update(objects=manager.BaseManager.from_queryset(QuerySet)())
        cls = super().__new__(mcs, name, bases, attrs)
        return cls


class Model(Model, metaclass=ModelBase):
    class Meta:
        abstract = True

    def values(self, *names):
        return ValueSet(self, names)

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
        names = ['get_{}'.format(name) for name in names]
        primary = self.cached_data('primary')
        auxiliary = self.cached_data('auxiliary')
        if names:
            data.update(self.values(*primary))
            data.update(self.values(*names))
        else:
            data.update(self.view())

        output = dict(name=str(self), type='object', data=data)
        if auxiliary:
            output.update(auxiliary=self.values(*auxiliary))
        return output

    def __str__(self):
        return '{} #{}'.format(self._meta.verbose_name, self.id)
