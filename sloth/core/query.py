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

from sloth.utils.http import XlsResponse, CsvResponse
from sloth.core.statistics import QuerySetStatistics
from sloth.exceptions import JsonReadyResponseException, HtmlJsonReadyResponseException, ReadyResponseException
from sloth.utils import getattrr, serialize, pretty


class QuerySet(models.QuerySet):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.metadata = dict(
            display=[], filters={}, search=[], ordering=[],
            page=1, limit=None, interval='', total=0, ignore=[],
            actions=[], attach=[], template=None, request=None, attr=None,
            global_actions=[], batch_actions=[], lookups=[], collapsed=True
        )

    def role_lookups(self, name, **scopes):
        self.metadata['lookups'].append((name, scopes))
        return self

    def apply_role_lookups(self, user):
        if user.is_superuser:
            return self
        lookups = []
        for name, scopes in self.metadata['lookups']:
            for scope_key, scope_value_attr in scopes.items():
                # self.metadata['ignore'].append(scope_key)
                role = user.roles.filter(name=name, scope_key=scope_key).first()
                if role:
                    lookups.append(Q(**{scope_value_attr: role.scope_value}))
        if lookups:
            return self.filter(reduce(operator.__and__, lookups))
        return self

    def _clone(self):
        clone = super()._clone()
        clone.metadata = dict(self.metadata)
        return clone

    def _get_list_search(self):
        return self.metadata['search']

    def _get_list_display(self):
        if self.metadata['display']:
            list_display = self.metadata['display']
        else:
            list_display = self.model.default_list_fields()
        return [name for name in list_display if name not in self.metadata['ignore']]

    def _get_list_filter(self):
        if self.metadata['filters']:
            list_filter = self.metadata['filters']
        else:
            list_filter = self.model.default_filter_fields()
        return [name for name in list_filter if name not in self.metadata['ignore']]

    def _get_list_ordering(self):
        return self.metadata['ordering']

    def _get_list_per_page(self):
        return self.metadata['limit'] or self.model.default_list_per_page()

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
                pretty(str(field.verbose_name)) if verbose else lookup
            ] = dict(key=lookup, name=pretty(str(field.verbose_name)), type=filter_type, choices=None)

        ordering = []
        for lookup in self._get_list_ordering():
            field = self.model.get_field(lookup)
            ordering.append(dict(id=lookup, text=field.verbose_name))
        if ordering:
            filters['Ordernação'] = dict(
                key='ordering', name='Ordenação', type='choices', choices=ordering
            )
        pagination = []
        for page in range(0, self.count() // self._get_list_per_page() + 1):
            start = page * self._get_list_per_page()
            end = start + self._get_list_per_page()
            pagination.append(dict(id=page + 1, text='{} - {}'.format(start + 1, end)))
        filters['Paginação'] = dict(
            key='pagination', name='Paginação', type='choices', choices=pagination
        )
        return filters

    def _get_attach(self, verbose=False):
        attach = {}
        if self.metadata['attach'] and not self.query.is_sliced:
            for i, name in enumerate(['all'] + self.metadata['attach']):
                attr = getattr(getattr(self.model.objects, '_queryset_class'), name)
                verbose_name = getattr(attr, 'verbose_name', name)
                if self.metadata['request']:
                    obj = getattr(self._clone(), name)().apply_role_lookups(self.metadata['request'].user)
                else:
                    obj = getattr(self._clone(), name)()
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

    # choices function

    def choices(self, request):
        filter_lookup = request.GET['choices']
        q = request.GET.get('term')
        field = self.model.get_field(filter_lookup)
        values = self.apply_role_lookups(request.user).values_list(
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

    # serialization function

    def to_list(self, wrap=False, verbose=False, formatted=False):
        data = []
        for obj in self:
            item = obj.values(*self._get_list_display()).load(verbose=verbose, formatted=formatted, size=False)
            data.append(dict(id=obj.id, description=str(obj), data=item, actions=self.get_obj_actions(obj)) if wrap else item)
        return data

    def export(self, limit=100):
        data = []
        header = []
        for i, obj in enumerate(self[0:limit]):
            if i == 0:
                for attr_name in self._get_list_display():
                    attr, value = getattrr(obj, attr_name)
                    header.append(getattr(attr, 'verbose_name', attr_name))
                data.append(header)
            row = []
            values = obj.values(*self._get_list_display()).load(verbose=False, size=False).values()
            for value in values:
                if value is None:
                    value = ''
                if isinstance(value, list) or isinstance(value, tuple) or hasattr(value, 'all'):
                    value = ', '.join([str(o) for o in value])
                row.append(serialize(value))
            data.append(row)
        return data

    def get_obj_actions(self, obj):
        actions = []
        for form_name in self.metadata['actions']:
            form_cls = self.model.action_form_cls(form_name)
            if self.metadata['request'] is None or form_cls.check_permission(
                    request=self.metadata['request'], instance=obj
            ):
                actions.append(form_cls.__name__)
        return actions

    def serialize(self, path=None, wrap=False, verbose=True, formatted=False):
        if wrap:
            verbose_name = str(self.model.metaclass().verbose_name_plural)
            icon = getattr(self.model.metaclass(), 'icon', None)
            search = self._get_search(verbose)
            display = self._get_display(verbose)
            filters = self._get_filters(verbose)
            attach = self._get_attach(verbose)
            values = self.paginate().to_list(wrap=wrap, verbose=verbose, formatted=formatted)
            pagination = dict(interval=self.metadata['interval'], total=self.metadata['total'])
            data = dict(
                uuid=uuid1().hex, type='queryset',
                name=verbose_name, icon=icon, count=self.count(),
                actions=dict(model=[], instance=[], queryset=[]),
                metadata=dict(search=search, display=display, filters=filters, pagination=pagination, collapsed=self.metadata['collapsed']),
                data=values
            )
            if attach:
                data.update(attach=attach)
            if path is None:
                if self.metadata['request'] and self.metadata['request'].is_ajax():
                    path = self.metadata['request'].path[4:]
                else:
                    path = '/{}/{}/'.format(self.model.metaclass().app_label, self.model.metaclass().model_name)
                    if self.metadata['attr']:
                        path = '{}{}/'.format(path, self.metadata['attr'])
            data.update(path=path)

            for action_type in ('global_actions', 'actions', 'batch_actions'):
                for form_name in self.metadata[action_type]:
                    form_cls = self.model.action_form_cls(form_name)
                    if action_type == 'actions' or self.metadata['request'] is None or form_cls.check_permission(
                            request=self.metadata['request'], instance=self.model()
                    ):
                        action = form_cls.get_metadata(
                            path, inline=action_type == 'actions', batch=action_type == 'batch_actions'
                        )
                        data['actions'][action['target']].append(action)
            template = self.metadata['template']
            if template is None:
                template = getattr(self.model.metaclass(), 'list_template', None)
            if template:
                template = template if template.endswith('.html') else '{}.html'.format(template)
                data.update(template=template)
            return data
        return self.to_list()

    def debug(self):
        print(json.dumps(self.serialize(wrap=True, verbose=True), indent=4, ensure_ascii=False))

    # metadata functions

    def list_display(self, *names):
        self.metadata['display'] = list(names)
        return self

    def search(self, q=None):
        if q:
            lookups = []
            for search_field in self._get_list_search() or self.model.default_search_fields():
                lookups.append(Q(**{'{}__icontains'.format(search_field): q}))
            return self.filter(reduce(operator.__or__, lookups))
        return self

    def search_fields(self, *names):
        self.metadata['search'] = list(names)
        return self

    def list_filter(self, *names):
        self.metadata['filters'] = list(names)
        return self

    def ordering(self, *names):
        self.metadata['ordering'] = list(names)
        return self

    def limit_per_page(self, size):
        self.metadata['limit'] = size
        return self

    def template(self, name):
        self.metadata['template'] = name
        return self

    def attach(self, *names):
        self.metadata['attach'] = list(names)
        return self

    def ignore(self, *names):
        self.metadata['ignore'] = list(names)
        return self

    def collapsed(self, flag=True):
        self.metadata['collapsed'] = flag
        return self

    def attr(self, name):
        self.metadata['attr'] = name
        return self

    # action functions

    def actions(self, *names):
        self.metadata['actions'] = list(names)
        return self

    def global_actions(self, *names):
        self.metadata['global_actions'] = list(names)
        return self

    def batch_actions(self, *names):
        self.metadata['batch_actions'] = list(names)
        return self

    def default_actions(self):
        if self.metadata['attr'] is None:
            self.metadata['actions'].extend(('edit', 'delete'))
            self.metadata['global_actions'].extend(('add',))
        return self

    # search and pagination functions

    def paginate(self, page=None):
        if page:
            start = (page - 1) * self._get_list_per_page()
            end = start + self._get_list_per_page()
            self.metadata['page'] = page
            self.metadata['interval'] = '{} - {}'.format(start + 1, end)
            return self
        else:
            self.metadata['interval'] = '{} - {}'.format(0 + 1, self._get_list_per_page())
            start = (self.metadata['page'] - 1) * self._get_list_per_page()
            end = start + self._get_list_per_page()
            self.metadata['interval'] = '{} - {}'.format(start + 1, end)
            return self.filter(pk__in=self.values_list('pk', flat=True)[start:end])

    # rendering function

    def html(self, uuid=None):
        data = self.serialize(wrap=True, verbose=True, formatted=True)
        if uuid:
            data['uuid'] = uuid
        return render_to_string(
            'adm/queryset/queryset.html',
            dict(data=data, uuid=uuid, messages=messages.get_messages(self.metadata['request'])),
            request=self.metadata['request']
        )

    def __str__(self):
        if self.metadata['request']:
            return self.html()
        return super().__str__()

    # request functions

    def contextualize(self, request):
        if request:
            self.metadata.update(request=request)
            if 'choices' in request.GET:
                raise JsonReadyResponseException(
                    self.choices(request)
                )
            if 'export' in request.GET:
                export = request.GET['export']
                if export == 'xls':
                    raise ReadyResponseException(
                        XlsResponse(
                            [([self.model.metaclass().verbose_name_plural, self.export()])]
                        )
                    )
                if export == 'csv':
                    raise ReadyResponseException(
                        CsvResponse(self.export())
                    )
            if 'attaches' in request.GET:
                raise JsonReadyResponseException(self._get_attach())
            if 'uuid' in request.GET:
                component = self.process_request(request).apply_role_lookups(request.user)
                raise HtmlJsonReadyResponseException(
                    component.html(
                        uuid=request.GET['uuid']
                    )
                )
            return self.apply_role_lookups(request.user)
        return self

    def process_request(self, request):
        page = 1
        attr_name = request.GET['subset']
        attach = self if attr_name == 'all' else getattr(self, attr_name)()
        if isinstance(attach, QuerySet):
            qs = attach
            if self.metadata['ignore']:
                qs.metadata['ignore'] = self.metadata['ignore']
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
            if qs.metadata['attr'] is None and request.GET.get('subset') == 'all':
                qs.default_actions()
            qs = qs.paginate(page)
            # qs.debug()
            return qs
        else:
            attach.qs = qs
            return attach

    # aggregation functions

    def count(self, x=None, y=None):
        if x:
            statistcs = QuerySetStatistics(self, x, y=y)
            return statistcs.contextualize(self.metadata['request'])
        total = super().count()
        self.metadata['total'] = total
        return total

    def sum(self, z, x=None, y=None):
        if x:
            if y:
                statistcs = QuerySetStatistics(self, x, y=y, func=Sum, z=z)
            else:
                statistcs = QuerySetStatistics(self, x, func=Sum, z=z)
            return statistcs.contextualize(self.metadata['request'])
        return self.aggregate(sum=Sum(z))['sum'] or 0
