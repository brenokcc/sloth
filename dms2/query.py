# -*- coding: utf-8 -*-
import datetime
import json
import math
import operator
from functools import reduce
from uuid import uuid1

from django.contrib import messages
from django.db import models
from django.db.models import Q
from django.db.models.aggregates import Sum
from django.template.loader import render_to_string

from .utils.http import XlsResponse, CsvResponse
from .statistics import QuerySetStatistics
from .exceptions import JsonReadyResponseException, HtmlJsonReadyResponseException, ReadyResponseException
from .forms import QuerySetForm
from .utils import getattrr


class QuerySet(models.QuerySet):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.metadata = dict(
            display=[], filters={}, search=[], ordering=[],
            page=1, limit=10, interval='1 - 10', total=0,
            actions=[], attach=[], template=None, request=None, attr=None
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
        for page in range(0, self.count() // self.metadata['limit'] + 1):
            start = page * self.metadata['limit']
            end = start + self.metadata['limit']
            pagination.append(dict(id=page + 1, text='{} - {}'.format(start + 1, end)))
        filters['Paginação'] = dict(
            key='pagination', name='Paginação', type='choices', choices=pagination
        )
        return filters

    def _get_attach(self, verbose=False):
        attach = {}
        if self.metadata['attach'] and not self.query.is_sliced:
            for i, name in enumerate(['all'] + self.metadata['attach']):
                attr = getattr(self.model.objects._queryset_class, name)
                verbose_name = getattr(attr, 'verbose_name', name)
                obj = getattr(self.model.objects, name)()
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
            item = obj.values(*self._get_list_display()).load(verbose=verbose, formatted=formatted, size=False)
            data.append(dict(id=obj.id, data=item, actions=self.get_obj_actions(obj)) if wrap else item)
        return data

    def get_obj_actions(self, obj):
        actions = []
        for form_name in self.metadata['actions']:
            form_cls = self.model.action_form_cls(form_name)
            if issubclass(form_cls, QuerySetForm) and not getattr(getattr(form_cls, 'Meta'), 'batch', False):
                if self.metadata['request'] is None or form_cls(request=self.metadata['request'],
                                                                instance=obj).has_permission():
                    actions.append(form_cls.__name__)
        return actions

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

    def debug(self):
        print(json.dumps(self.serialize(wrap=True, verbose=True), indent=4, ensure_ascii=False))

    def serialize(self, path=None, wrap=False, verbose=True, formatted=False):
        if wrap:
            verbose_name = str(self.model.metaclass().verbose_name_plural)
            icon = getattr(self.model.metaclass(), 'icon', None)
            search = self._get_search(verbose)
            display = self._get_display(verbose)
            filters = self._get_filters(verbose)
            attach = self._get_attach(verbose)
            pagination = dict(interval=self.metadata['interval'], total=self.metadata['total'])
            data = dict(
                uuid=uuid1().hex, type='queryset',
                name=verbose_name, icon=icon, count=self.count(),
                actions=dict(model=[], instance=[], queryset=[]),
                metadata=dict(search=search, display=display, filters=filters, pagination=pagination),
                data=self.paginate().to_list(wrap=wrap, verbose=verbose, formatted=formatted)
            )
            if attach:
                data.update(attach=attach)
            if path is None:
                path = '/{}/{}/'.format(self.model.metaclass().app_label, self.model.metaclass().model_name)
                if self.metadata['attr']:
                    path = '{}{}/'.format(path, self.metadata['attr'])
            data.update(path=path)

            for form_name in self.metadata['actions']:
                form_cls = self.model.action_form_cls(form_name)
                if not issubclass(form_cls, QuerySetForm):
                    if self.metadata['request'] and not form_cls(request=self.metadata['request']).has_permission():
                        continue
                action = form_cls.get_metadata(path)
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

    def attr(self, name):
        self.metadata['attr'] = name
        return self

    def add_default_actions(self):
        self.metadata['actions'].extend(('add', 'edit-inline', 'delete-inline'))
        return self

    def html(self, uuid=None):
        data = self.serialize(wrap=True, verbose=True, formatted=True)
        if uuid:
            data['uuid'] = uuid
        return render_to_string(
            'adm/queryset.html',
            dict(data=data, uuid=uuid, messages=messages.get_messages(self.metadata['request'])),
            request=self.metadata['request']
        )

    def contextualize(self, request):
        if request:
            self.metadata.update(request=request)
            if 'choices' in request.GET:
                raise JsonReadyResponseException(
                    self.choices(request.GET['choices'], q=request.GET.get('term'))
                )
            if 'export' in request.GET:
                export = request.GET['export']
                if export == 'xls':
                    raise ReadyResponseException(
                        XlsResponse([('Dados', [])])
                    )
                if export == 'csv':
                    raise ReadyResponseException(
                        CsvResponse([])
                    )
            if 'attaches' in request.GET:
                raise JsonReadyResponseException(self._get_attach())
            if 'uuid' in request.GET:
                component = self.process_params(request)
                raise HtmlJsonReadyResponseException(
                    component.html(
                        uuid=request.GET['uuid']
                    )
                )
        return self

    def paginate(self, page=None):
        if page:
            start = (page - 1) * self.metadata['limit']
            end = start + self.metadata['limit']
            self.metadata['page'] = page
            self.metadata['interval'] = '{} - {}'.format(start + 1, end)
            return self
        else:
            start = (self.metadata['page'] - 1) * self.metadata['limit']
            end = start + self.metadata['limit']
            return self[start:end]

    def process_params(self, request):
        page = 1
        attr_name = request.GET['subset']
        attach = self if attr_name == 'all' else getattr(self.model.objects, attr_name)()
        if isinstance(attach, QuerySet):
            qs = attach
        elif isinstance(attach, QuerySetStatistics):
            qs = attach.qs
        else:
            raise Exception()
        qs.metadata.update(request=request)
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
            if qs.metadata['attr'] is None:
                qs.add_default_actions()
            qs = qs.paginate(page)
            # qs.debug()
            return qs
        else:
            attach.qs = qs
            return attach

    def count(self, x=None, y=None):
        if x:
            return QuerySetStatistics(self, x, y=y)
        total = super().count()
        self.metadata['total'] = total
        return total

    def sum(self, x, y=None, z=None):
        if y:
            return QuerySetStatistics(self, x, y=y, func=Sum, z=z)
        else:
            return QuerySetStatistics(self, x, func=Sum, z=z)