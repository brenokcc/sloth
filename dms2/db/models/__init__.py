# -*- coding: utf-8 -*-
from uuid import uuid1

import math
import json
import operator
import datetime
from decimal import Decimal
from django.contrib import messages
from django.core.exceptions import FieldDoesNotExist
from django.db.models import Q
from functools import reduce
from django.apps import apps
from django.db import models
from django.db.models import manager
from django.template.loader import render_to_string
from django.db.models.aggregates import Sum, Count

from dms2.exceptions import ReadyResponseException, HtmlReadyResponseException
from dms2.forms import ModelForm, QuerySetForm
from dms2.utils import getattrr, serialize
from dms2.db.models.decorators import meta
from dms2 import formatters
from django.db.models import options


setattr(options, 'DEFAULT_NAMES', options.DEFAULT_NAMES + (
    'icon', 'display', 'search', 'limit', 'filters'
))


FILTER_FIELD_TYPES = 'BooleanField', 'NullBooleanField', 'ForeignKey', 'ForeignKeyPlus', 'DateField', 'DateFieldPlus'
SEARCH_FIELD_TYPES = 'CharField', 'CharFieldPlus', 'TextField'


class ValueSet(dict):
    def __init__(self, instance, names, image=None):
        self.instance = instance
        self.request = None
        self.metadata = dict(model=type(instance), names={}, metadata=[], actions=[], attach=[], append=[], image=image, template=None)
        for attr_name in names:
            if isinstance(attr_name, tuple):
                for name in attr_name:
                    self.metadata['names'][name] = 100//len(attr_name)
            else:
                self.metadata['names'][attr_name] = 100
        super().__init__()

    def actions(self, *names):
        self.metadata['actions'] = list(names)
        return self

    def append(self, *names):
        self.metadata['append'] = list(names)
        return self

    def attach(self, *names):
        self.metadata['attach'] = list(names)
        return self

    def image(self, image):
        self.metadata['image'] = image
        return self

    def template(self, name):
        self.metadata['template'] = name
        return self

    def contextualize(self, request):
        self.request = request
        if request.is_ajax():
            raise HtmlReadyResponseException(
                self.html(partial=True)
            )
        return self

    def load(self, wrap=False, verbose=False, add_width=False, formatted=False):
        if self.metadata['names']:
            metadata = getattr(self.instance, '_meta')
            for attr_name, width in self.metadata['names'].items():
                attr, value = getattrr(self.instance, attr_name)
                path = '/{}/{}/{}/{}/'.format(metadata.app_label, metadata.model_name, self.instance.pk, attr_name)
                if isinstance(value, QuerySet):
                    value.contextualize(self.request)
                    verbose_name = getattr(attr, 'verbose_name', attr_name) if verbose else attr_name
                    if wrap:
                        value = value.serialize(path=path, wrap=wrap, verbose=verbose, formatted=formatted)
                        value['name'] = verbose_name
                    else:
                        value = [str(o) for o in value]
                elif isinstance(value, QuerySetStatistics):
                    verbose_name = getattr(attr, 'verbose_name', attr_name) if verbose else attr_name
                    value = value.serialize(path=path, wrap=wrap)
                    if wrap:
                        value['name'] = verbose_name
                elif isinstance(value, ValueSet):
                    key = attr_name
                    actions = getattr(value, 'metadata')['actions']
                    image_attr_name = getattr(value, 'metadata')['image']
                    template = getattr(value, 'metadata')['template']
                    verbose_name = getattr(attr, 'verbose_name', attr_name) if verbose else attr_name
                    if attr_name == 'fieldset':
                        key = None
                        path = None
                    value.load(wrap=wrap, verbose=verbose, add_width=self.get_type() == 'fieldset', formatted=formatted)
                    value = dict(uuid=uuid1().hex, type=value.get_type(), name=verbose_name, key=key, actions=[], data=value, path=path) if wrap else value
                    if wrap:
                        for form_name in actions:
                            action = self.instance.action_form_cls(form_name).get_metadata(path)
                            value['actions'].append(action)
                            print(form_name, value['path'])
                        value['path'] = path
                        if image_attr_name:
                            image_attr = getattr(self.instance, image_attr_name)
                            image = image_attr() if callable(image_attr) else image_attr
                            if image:
                                value['image'] = image
                        if template:
                            value['template'] = '{}.html'.format(template)
                elif formatted and hasattr(attr, 'formatter'):
                    formatters.initilize()
                    formatter_cls = formatters.FORMATTERS[attr.formatter]
                    value = formatter_cls(value, instance=self.instance).render()
                else:
                    value = serialize(value)

                if wrap and add_width:
                    value = dict(value=value, width=width)
                if verbose:
                    self[self.metadata['model'].get_attr_verbose_name(attr_name)[0]] = value
                else:
                    self[attr_name] = value
        else:
            self['id'] = self.instance.id
            self[self.metadata['model'].__name__.lower()] = str(self.instance)
        return self

    def __str__(self):
        return json.dumps(self, indent=4, ensure_ascii=False)

    def get_type(self):
        for value in self.values():
            if isinstance(value, dict) and value.get('type') in ('queryset', 'fieldset'):
                return 'fieldsets'
        return 'fieldset'

    def serialize(self, wrap=False, verbose=False, formatted=False, request=None):
        self.load(wrap=wrap, verbose=verbose, formatted=formatted)
        if wrap:
            data = {}
            data.update(self)
            metadata = getattr(self.instance, '_meta')
            icon = getattr(metadata, 'icon', None)
            output = dict(
                uuid=uuid1().hex, type='object', name=str(self.instance),
                icon=icon, data=data, actions=[], attach=[], append={}
            )
            for form_name in self.metadata['actions']:
                path = '/{}/{}/{}/'.format(metadata.app_label, metadata.model_name, self.instance.pk)
                action = self.instance.action_form_cls(form_name).get_metadata(path)
                output['actions'].append(action)
            for attr_name in self.metadata['attach']:
                name = getattr(getattr(self.instance, attr_name), 'verbose_name', attr_name)
                path = '/{}/{}/{}/{}/'.format(metadata.app_label, metadata.model_name, self.instance.pk, attr_name)
                output['attach'].append(dict(name=name, path=path))
            for attr_name in self.metadata['append']:
                output['append'].update(self.instance.values(attr_name).load(wrap=wrap, verbose=verbose, formatted=formatted))
            return output
        else:
            if len(self.metadata['names']) == 1:
                return self[list(self.metadata['names'].keys())[0]]
            return self

    def html(self, uuid=None, partial=False):
        if partial:
            icon = None
            name = None
            actions = []
            attach = []
            append = []
            data = self.load(wrap=True, verbose=True)
        else:
            serialized = self.serialize(wrap=True, verbose=True, formatted=True, request=None)
            icon = serialized['icon']
            name = serialized['name']
            data = serialized['data']
            actions = serialized['actions']
            attach = serialized['attach']
            append = serialized['append']
        if uuid:
            data['uuid'] = uuid
        return render_to_string(
            'adm/valueset.html',
            dict(uuid=uuid, icon=icon, name=name, data=data, actions=actions, attach=attach, append=append)
        )


class QuerySet(models.QuerySet):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.metadata = dict(
            display=[], filters={}, search=[], ordering=[], limit=10, actions=[], attach=[], template=None
        )

    def _clone(self):
        clone = super()._clone()
        clone.metadata = dict(self.metadata)
        return clone

    def _get_list_search(self):
        return self.metadata['search']

    def _get_list_display(self):
        if self.metadata['display']:
            return self.metadata['display']
        return self.model.default_list_fields()

    def _get_list_filter(self):
        if self.metadata['filters']:
            return self.metadata['filters']
        return self.model.default_filter_fields()

    def _get_list_ordering(self):
        return self.metadata['ordering']

    def _get_search(self, verbose=False):
        display = {}
        for lookup in self._get_list_search() or self.model.default_search_fields():
            verbose_name, _ = self.model.get_attr_verbose_name(lookup)
            display[verbose_name if verbose else lookup] = dict(key=lookup, name=verbose_name)
        return display

    def _get_display(self, verbose=False):
        display = {}
        for lookup in self._get_list_display():
            verbose_name, sort = self.model.get_attr_verbose_name(lookup)
            display[verbose_name if verbose else lookup] = dict(key=lookup, name=verbose_name, sort=sort)
        return display

    def _get_filters(self, verbose=False):
        filters = {}
        for lookup in self._get_list_filter():
            field = self.model.get_field(lookup)
            field_type_name = type(field).__name__
            filter_type = 'choices'
            if 'Boolean' in field_type_name:
                filter_type = 'boolean'
            elif 'DateTime' in field_type_name:
                filter_type = 'datetime'
            elif 'Date' in field_type_name:
                filter_type = 'date'
            filters[
                str(field.verbose_name) if verbose else lookup
            ] = dict(key=lookup, name=field.verbose_name, type=filter_type, choices=None)

        ordering = []
        for lookup in self._get_list_ordering():
            field = self.model.get_field(lookup)
            ordering.append(dict(id=lookup, text=field.verbose_name))
        if ordering:
            filters['Ordernação'] = dict(
                key='ordering', name='Ordenação', type='choices', choices=ordering
            )
        pagination = []
        for page in range(0, self.count()//self.metadata['limit'] + 1):
            start = page * self.metadata['limit']
            end = start + self.metadata['limit']
            pagination.append(dict(id=page+1, text='{} - {}'.format(start + 1, end)))
        filters['Paginação'] = dict(
            key='pagination', name='Paginação', type='choices', choices=pagination
        )
        return filters

    def _get_attach(self, verbose=False):
        attach = {}
        if self.metadata['attach'] and not self.query.is_sliced:
            for i, name in enumerate(['all'] + self.metadata['attach']):
                attr = getattr(self, name)
                verbose_name = getattr(attr, 'verbose_name', name)
                obj = attr()
                if isinstance(obj, QuerySet):
                    if verbose_name == 'all':
                        verbose_name = 'Tudo'
                    attach[verbose_name if verbose else name] = dict(
                        name=verbose_name, key=name, count=obj.count(), active=i == 0
                    )
                else:
                    attach[verbose_name if verbose else name] = dict(
                        name=verbose_name, key=name, active=i == 0
                    )
        return attach

    def to_list(self, wrap=False, verbose=False, formatted=False):
        data = []
        for obj in self:
            item = obj.values(*self._get_list_display()).serialize(verbose=verbose, formatted=formatted)
            data.append([obj.id, item] if wrap else item)
        return data

    def choices(self, filter_lookup, q=None):
        field = getattrr(self.model, filter_lookup)[0].field
        values = self.values_list(
            filter_lookup, flat=True
        ).order_by(filter_lookup).order_by(filter_lookup).distinct()
        if field.related_model:
            qs = field.related_model.objects.filter(id__in=values)
            qs = qs.search(q=q) if q else qs
            qs = qs.distinct()
            total = values.count()
            items = [dict(id=value.id, text=str(value)) for value in qs[0:25]]
        else:
            total = values.count()
            items = [dict(id=value, text=str(value)) for value in values]
        return dict(
            total=total, page=1, pages=math.ceil((1.0 * total) / 25),
            q=q, items=items
        )

    def serialize(self, path=None, wrap=False, verbose=True, formatted=False):
        if wrap:
            metadata = getattr(self.model, '_meta')
            verbose_name = str(getattr(self.model, '_meta').verbose_name_plural)
            icon = getattr(metadata, 'icon', None)
            search = self._get_search(verbose)
            display = self._get_display(verbose)
            filters = self._get_filters(verbose)
            attach = self._get_attach(verbose)
            data = dict(
                uuid=uuid1().hex, type='queryset',
                name=verbose_name, icon=icon, count=self.count(),
                actions=dict(model=[], instance=[], queryset=[]),
                metadata=dict(search=search, display=display, filters=filters),
                data=self.paginate().to_list(wrap=wrap, verbose=verbose, formatted=formatted)
            )
            if attach:
                data.update(attach=attach)
            if path is None:
                path = '/{}/{}/'.format(metadata.app_label, metadata.model_name)
            data.update(path=path)

            for form_name in self.metadata['actions']:
                action = self.model.action_form_cls(form_name).get_metadata(path)
                data['actions'][action['target']].append(action)
            data.update(path=path)
            if self.metadata['template']:
                data.update(template='{}.html'.format(self.metadata['template']))
            return data
        return self.to_list()

    def display(self, *names):
        self.metadata['display'] = list(names)
        return self

    def search(self, *names, q=None):
        if q:
            lookups = []
            for search_field in self._get_list_search() or self.model.default_search_fields():
                lookups.append(Q(**{'{}__icontains'.format(search_field): q}))
            return self.filter(reduce(operator.__or__, lookups))
        self.metadata['search'] = list(names)
        return self

    def filters(self, *names):
        self.metadata['filters'] = list(names)
        return self

    def ordering(self, *names):
        self.metadata['ordering'] = list(names)
        return self

    def limit(self, size):
        self.metadata['limit'] = size
        return self

    def template(self, name):
        self.metadata['template'] = name
        return self

    def attach(self, *names):
        self.metadata['attach'] = list(names)
        return self

    def actions(self, *names):
        self.metadata['actions'] = list(names)
        return self

    def add_default_actions(self):
        self.metadata['actions'].extend(('add', 'edit-inline', 'delete-inline'))
        return self

    def html(self, uuid=None, request=None):
        data = self.serialize(wrap=True, verbose=True, formatted=True)
        if uuid:
            data['uuid'] = uuid

        return render_to_string(
            'adm/queryset.html',
            dict(data=data, uuid=uuid, messages=messages.get_messages(request))
        )

    def contextualize(self, request, add_default_actions=False):
        if request:
            if add_default_actions:
                self.add_default_actions()
            if 'choices' in request.GET:
                raise ReadyResponseException(
                    self.choices(request.GET['choices'], q=request.GET.get('term'))
                )
            if 'uuid' in request.GET:
                raise HtmlReadyResponseException(
                    self.process_params(request).html(
                        uuid=request.GET['uuid'],
                        request=request
                    )
                )
        return self

    def paginate(self, page=1):
        start = (page - 1) * self.metadata['limit']
        end = start + self.metadata['limit']
        return self[start:end]

    def process_params(self, request):
        page = 1
        attr_name = request.GET['subset']
        if attr_name != 'all' and attr_name not in self.metadata['attach']:
            raise ValueError('"{}" is an invalid attach.'.format(attr_name))
        attach = self if attr_name == 'all' else getattr(self, attr_name)()
        if isinstance(attach, QuerySet):
            qs = attach
        elif isinstance(attach, QuerySetStatistics):
            qs = attach.qs
        else:
            raise Exception()
        for item in self._get_filters().values():
            value = request.GET.get(item['key'])
            if value:
                if item['key'] == 'ordering':
                    qs = qs.order_by(value)
                elif item['key'] == 'pagination':
                    page = int(value)
                else:
                    if item['type'] == 'date':
                        value = datetime.datetime.strptime(value, '%d/%m/%Y')
                    if item['type'] == 'boolean':
                        value = bool(int(value))
                    qs = qs.filter(**{item['key']: value})
        if 'q' in request.GET:
            qs = qs.search(q=request.GET['q'])
        if isinstance(attach, QuerySet):
            return qs.add_default_actions().paginate(page)
        else:
            attach.qs = qs
            return attach

    def count(self, x=None, y=None):
        return QuerySetStatistics(self, x, y=y) if x else super().count()

    def sum(self, x, y=None, z=None):
        if y:
            return QuerySetStatistics(self, x, y=y, func=Sum, z=z)
        else:
            return QuerySetStatistics(self, x, func=Sum, z=z)


class QuerySetStatistics(object):
    MONTHS = ('JAN', 'FEV', 'MAR', 'ABR', 'MAI', 'JUN', 'JUL', 'AGO', 'SET', 'OUT', 'NOV', 'DEZ')

    def __init__(self, qs, x, y=None, func=None, z='id'):
        self.qs = qs
        self.x = x
        self.y = y
        self.func = func or Count
        self.z = z
        self._xfield = None
        self._yfield = None
        self._xdict = {}
        self._ydict = {}
        self._values_dict = None

        if '__month' in x:
            self._xdict = {i + 1: month for i, month in enumerate(QuerySetStatistics.MONTHS)}
        if y and '__month' in y:
            self._ydict = {i + 1: month for i, month in enumerate(QuerySetStatistics.MONTHS)}

    def _calc(self):
        if self._values_dict is None:
            self.calc()

    def _xfield_display_value(self, value):
        if hasattr(self._xfield, 'choices') and self._xfield.choices:
            for choice in self._xfield.choices:
                if choice[0] == value:
                    return choice[1]
        return value

    def _yfield_display_value(self, value):
        if hasattr(self._yfield, 'choices') and self._yfield.choices:
            for choice in self._yfield.choices:
                if choice[0] == value:
                    return choice[1]
        return value

    def _clear(self):
        self._xfield = None
        self._yfield = None
        self._xdict = {}
        self._ydict = {}
        self._values_dict = None

    def calc(self):
        self._values_dict = {}
        values_list = self.qs.values_list(self.x, self.y).annotate(
            self.func(self.z)) if self.y else self.qs.values_list(self.x).annotate(self.func(self.z))

        self._xfield = self.qs.model.get_field(self.x.replace('__year', '').replace('__month', ''))
        if self._xdict == {}:
            xvalues = self.qs.values_list(self.x, flat=True).order_by(self.x).distinct()
            if self._xfield.related_model:
                self._xdict = {
                    obj.pk: str(obj) for obj in self._xfield.related_model.objects.filter(pk__in=xvalues)
                }
            else:
                self._xdict = {
                    value: value for value in self.qs.values_list(self.x, flat=True)
                }
            if None in xvalues:
                self._xdict[None] = 'Não-Informado'
        if self.y:
            self._yfield = self.qs.model.get_field(self.y.replace('__year', '').replace('__month', ''))
            yvalues = self.qs.values_list(self.y, flat=True).order_by(self.y).distinct()
            if self._ydict == {}:
                if self._yfield.related_model:
                    self._ydict = {
                        obj.pk: str(obj) for obj in self._yfield.related_model.objects.filter(pk__in=yvalues)
                    }
                else:
                    self._ydict = {
                        value: value for value in yvalues
                    }
            self._values_dict = {(vx, vy): calc for vx, vy, calc in values_list}
            if None in yvalues:
                self._ydict[None] = 'Não-Informado'
        else:
            self._ydict = {}
            self._values_dict = {(vx, None): calc for vx, calc in values_list}

    def filter(self, **kwargs):
        self._clear()
        self.qs = self.qs.filter(**kwargs)
        return self

    def apply_lookups(self, user, lookups=None):
        self._clear()
        self.qs = self.qs.apply_lookups(user, lookups=lookups)
        return self

    def serialize(self, wrap=True, verbose=True, path=None):
        self._calc()
        series = dict()
        formatter = {True: 'Sim', False: 'Não', None: ''}

        def format_value(value):
            return isinstance(value, Decimal) and '{0:.2f}'.format(value) or value

        if self._ydict:

            for i, (yk, yv) in enumerate(self._ydict.items()):
                data = []
                for j, (xk, xv) in enumerate(self._xdict.items()):
                    data.append([formatter.get(xv, str(xv)), format_value(self._values_dict.get((xk, yk), 0)), '#EEE'])
                series.update(**{formatter.get(yv, str(yv)): data})
        else:
            data = list()
            for j, (xk, xv) in enumerate(self._xdict.items()):
                data.append([formatter.get(xv, str(xv)), format_value(self._values_dict.get((xk, None), 0)), '#EEE'])
            series['default'] = data

        return dict(
            type='statistics',
            name=None,
            path=path,
            series=series
        )

    def html(self, uuid=None, request=None):
        data = self.serialize(wrap=True, verbose=True)
        return render_to_string('adm/statistics.html', dict(data=data))


class BaseManager(manager.BaseManager):
    def get_queryset(self):
        return super().get_queryset().all()


class Manager(BaseManager.from_queryset(QuerySet)):
    pass


class ModelMixin(object):

    def init_one_to_one_fields(self):
        for field in getattr(self, '_meta').fields:
            if isinstance(field, models.OneToOneField):
                if getattr(self, '{}_id'.format(field.name)) is None:
                    setattr(self, field.name, field.related_model())

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
        return ValueSet(self, names)

    @meta('Dados Gerais')
    def fieldset(self):
        model = type(self)
        names = [field.name for field in getattr(model, '_meta').fields[0:5]]
        return self.values(*names)

    def view(self):
        return self.values('fieldset')

    def serialize(self, wrap=True, verbose=True):
        return self.view().serialize(wrap=wrap, verbose=verbose)

    def get_absolute_url(self, prefix=''):
        return '{}/{}/{}/{}/'.format(prefix, self._meta.app_label, self._meta.model_name, self.pk)

    def __str__(self):
        return '{} #{}'.format(self._meta.verbose_name, self.pk)

    @classmethod
    def add_form_cls(cls):

        class Add(ModelForm):
            class Meta:
                model = cls
                exclude = ()
                name = 'Cadastrar {}'.format(cls._meta.verbose_name)
                icon = 'plus'
                style = 'success'

            def process(self):
                self.save()
                self.notify('Cadastro realizado com sucesso')

        return Add

    @classmethod
    def edit_form_cls(cls, inline=False):

        class Edit(QuerySetForm if inline else ModelForm):
            class Meta:
                model = cls
                exclude = ()
                name = 'Editar {}'.format(cls._meta.verbose_name)
                icon = 'pencil'
                style = 'primary'

            def process(self):
                self.save()
                self.notify('Edição realizada com sucesso')

        return Edit

    @classmethod
    def delete_form_cls(cls, inline=False):

        class Delete(QuerySetForm if inline else ModelForm):
            class Meta:
                model = cls
                fields = ()
                name = 'Excluir {}'.format(cls._meta.verbose_name)
                icon = 'x'
                style = 'danger'

            def process(self):
                self.instance.delete()
                self.notify('Exclusão realizada com sucesso')

        return Delete

    @classmethod
    def action_form_cls(cls, action):
        if action.lower() == 'add':
            return cls.add_form_cls()
        elif action.lower() == 'edit':
            return cls.edit_form_cls()
        elif action.lower() == 'delete':
            return cls.delete_form_cls()
        elif action.lower() == 'edit-inline':
            return cls.edit_form_cls(inline=True)
        elif action.lower() == 'delete-inline':
            return cls.delete_form_cls(inline=True)
        else:
            config = apps.get_app_config(cls._meta.app_label)
            forms = __import__(
                '{}.forms'.format(config.module.__package__),
                fromlist=config.module.__package__.split()
            )
            for name in dir(forms):
                if name.lower() == action.lower():
                    return getattr(forms, name)
            return None

    @classmethod
    def get_field(cls, lookup):
        model = cls
        attrs = lookup.split('__')
        while attrs:
            attr_name = attrs.pop(0)
            if attrs:  # go deeper
                field = getattr(model, '_meta').get_field(attr_name)
                model = field.related_model
            else:
                try:
                    return getattr(model, '_meta').get_field(attr_name)
                except FieldDoesNotExist:
                    pass
        return None

    @classmethod
    def default_list_fields(cls, exclude=None):
        return [field.name for field in cls._meta.fields[0:5] if field.name != exclude]

    @classmethod
    def default_filter_fields(cls, exclude=None):
        filters = []
        for field in cls._meta.fields:
            cls_name = type(field).__name__
            if cls_name in FILTER_FIELD_TYPES:
                if field.name != exclude:
                    filters.append(field.name)
            elif field.choices:
                if field.name != exclude:
                    filters.append(field.name)
        return filters

    @classmethod
    def default_search_fields(cls):
        search = []
        for field in cls._meta.fields:
            cls_name = type(field).__name__
            if cls_name in SEARCH_FIELD_TYPES:
                search.append(field.name)
        return search

    @classmethod
    def get_attr_verbose_name(cls, lookup):
        field = cls.get_field(lookup)
        if field:
            return str(field.verbose_name), True
        attr = getattr(cls, lookup)
        return getattr(attr, 'verbose_name', lookup), False

    @classmethod
    def get_api_paths(cls):
        instance = cls()
        instance.init_one_to_one_fields()
        url = '/api/{}/{}/'.format(cls._meta.app_label, cls._meta.model_name)

        info = dict()
        info[url] = [('get', 'List', 'List objects', {'type': 'string'})]
        info['{}{{id}}/'.format(url)] = [
            ('get', 'View', 'View object', {'type': 'string'}),
            ('post', 'Add', 'Add object', {'type': 'string'}),
            ('put', 'Edit', 'Edit object', {'type': 'string'}),
        ]
        for name, attr in cls.__dict__.items():
            if hasattr(attr, 'decorated'):
                v = getattr(instance, name)()
                info['{}{{id}}/{}/'.format(url, name)] = [
                    ('get', attr.verbose_name, 'View {}'.format(attr.verbose_name), {'type': 'string'}),
                ]
                if isinstance(v, ValueSet):
                    for action in v.metadata['actions']:
                        info['{}{{id}}/{}/{{ids}}/{}/'.format(url, name, action)] = [
                            ('post', action, 'Execute {}'.format(action), {'type': 'string'}),
                        ]
                elif isinstance(v, QuerySet):
                    for action in v.metadata['actions']:
                        info['{}{{id}}/{}/{{ids}}/{}/'.format(url, name, action)] = [
                            ('post', action, 'Execute {}'.format(action), {'type': 'string'}),
                        ]

        paths = {}
        for url, data in info.items():
            paths[url] = {}
            for method, summary, description, schema in data:
                paths[url][method] = {
                    'summary': summary,
                    'description': description,
                    'responses': {
                        '200': {'description': 'OK', 'content': {'application/json': {'schema': schema}}}
                    },
                    'tags': [cls._meta.app_label],
                    'security': [dict(OAuth2=[], BasicAuth=[])]  # , BearerAuth=[], ApiKeyAuth=[]
                }
        return paths
