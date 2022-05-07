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
from django.db.models.aggregates import Sum, Count
from django.template.loader import render_to_string

from sloth.utils.http import XlsResponse, CsvResponse
from sloth.core.statistics import QuerySetStatistics
from sloth.exceptions import JsonReadyResponseException, HtmlJsonReadyResponseException, ReadyResponseException
from sloth.utils import getattrr, serialize, pretty


class QuerySet(models.QuerySet):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.metadata = dict(uuid=uuid1().hex,
            display=[], view=['self'], filters={}, dfilters={}, search=[], ordering=[],
            page=1, limit=None, interval='', total=0, ignore=[], is_admin=False,
            actions=[], attach=[], template=None, request=None, attr=None, source=None,
            global_actions=[], batch_actions=[], lookups=[], collapsed=True, compact=False, verbose_name=None,
            totalizer=None, calendar=None
        )

    def normalize_email(self, *args, **kwargs):
        pass

    def role_lookups(self, *names, **scopes):
        for name in names:
            self.metadata['lookups'].append((name, scopes))
        return self

    def apply_role_lookups(self, user):
        if user.is_superuser:
            return self
        if self.metadata['lookups']:
            lookups = []
            for name, scopes in self.metadata['lookups']:
                if scopes:
                    for scope_value_attr, scope_key in scopes.items():
                        for scope_value in user.roles.filter(name=name, scope_key=scope_key).values_list('scope_value', flat=True):
                            lookups.append(Q(**{scope_value_attr: scope_value}))
                else:
                    if user.roles.contains(name):
                        return self
            if lookups:
                return self.filter(reduce(operator.__or__, lookups))
            return self.none()
        return self

    def join(self, *names):
        from sloth.core.values import ValueSet
        return ValueSet(self, names)

    def _clone(self):
        clone = super()._clone()
        clone.metadata = dict(self.metadata)
        return clone

    def _get_list_search(self):
        return self.metadata['search']

    def _get_list_display(self, add_id=False):
        if self.metadata['display']:
            list_display = self.metadata['display']
        else:
            list_display = self.model.default_list_fields()
        display = [name for name in list_display if name not in self.metadata['ignore']]
        if add_id:
            display.insert(0, 'id')
        return display

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
            verbose_name, _, _ = self.model.get_attr_metadata(lookup)
            display[verbose_name if verbose else lookup] = dict(key=lookup, name=verbose_name)
        return display

    def _get_display(self, verbose=False):
        display = {}
        for lookup in self._get_list_display():
            verbose_name, sort, template = self.model.get_attr_metadata(lookup)
            display[pretty(verbose_name) if verbose else lookup] = dict(
                key=lookup, name=pretty(verbose_name), sort=sort, template=template
            )
        return display

    def _get_filters(self, verbose=False):
        filters = {}
        list_filter = self._get_list_filter()
        list_filter.extend(self.metadata['dfilters'])
        for lookup in list_filter:
            field = self.model.get_field(lookup)
            field_type_name = type(field).__name__
            filter_type = 'choices'
            if 'Boolean' in field_type_name:
                filter_type = 'boolean'
            elif 'DateTime' in field_type_name:
                filter_type = 'datetime'
            elif 'Date' in field_type_name:
                filter_type = 'date'
            if lookup in self.metadata['dfilters']:
                qs = self.order_by(lookup).values_list(lookup).distinct()[1:2]
                if not qs:
                    continue

            key = pretty(str(field.verbose_name)) if verbose else lookup
            name = pretty(str(field.verbose_name))
            if filter_type in ('datetime', 'date'):
                for sublookup, symbol in dict(gte='>', lte='<').items():
                    k = '{} {}'.format(symbol, key) if verbose else '{}__{}'.format(key, sublookup)
                    n = '{} {}'.format(symbol, name)
                    hidden = lookup == self.metadata['calendar']
                    filters[k] = dict(key='{}__{}'.format(
                        lookup, sublookup), name=n, type=filter_type, choices=None, hidden=hidden
                    )
            else:
                filters[key] = dict(
                    key=lookup, name=name, type=filter_type, choices=None, hidden=False
                )

        ordering = []
        for lookup in self._get_list_ordering():
            field = self.model.get_field(lookup)
            ordering.append(dict(id=lookup, text=field.verbose_name))
        if ordering:
            filters['Ordernação'] = dict(
                key='ordering', name='Ordenação', type='choices', choices=ordering
            )
        return filters

    def _get_attach(self, verbose=False):
        attaches = {}
        if self.metadata['attach'] and not self.query.is_sliced:
            for i, name in enumerate(['all'] + self.metadata['attach']):
                attach = getattr(self._clone(), name)()
                if self.metadata['request'] and hasattr(attach, 'apply_role_lookups'):
                    attach = attach.apply_role_lookups(self.metadata['request'].user)
                verbose_name = attach.metadata['verbose_name'] or pretty(name)
                if isinstance(attach, QuerySet):
                    if name == 'all':
                        verbose_name = 'Tudo'
                    attaches[verbose_name if verbose else name] = dict(
                        name=verbose_name, key=name, count=attach.count(), active=i == 0
                    )
                else:
                    attaches[verbose_name if verbose else name] = dict(
                        name=verbose_name, key=name, active=i == 0
                    )
        return attaches

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

    # calendar

    def calendar(self, name):
        self.metadata['calendar'] = name
        return self

    def to_calendar(self):
        days = {}
        attr_name = self.metadata['calendar']
        start = self.metadata['request'].GET.get('{}__gte'.format(attr_name))
        if start:
            start = datetime.datetime.strptime(start, '%d/%m/%Y').date()
        else:
            start = self.order_by(attr_name).values_list(attr_name, flat=True).first() or datetime.date.today()
        first_day_of_month = datetime.date(start.year, start.month, 1)
        first_day_of_calendar = first_day_of_month - datetime.timedelta(days=first_day_of_month.weekday())
        for i in range(0, (first_day_of_month - first_day_of_calendar).days):
            days[first_day_of_calendar + datetime.timedelta(days=i)] = None
        last_day_of_month = first_day_of_month + datetime.timedelta(days=0)
        while first_day_of_month.month == last_day_of_month.month:
            days[last_day_of_month] = 0
            last_day_of_month += datetime.timedelta(days=1)
        last_day_of_month += datetime.timedelta(days=-1)
        last_day_of_calendar = last_day_of_month + datetime.timedelta(days=0)
        while last_day_of_calendar.weekday() < 6:
            last_day_of_calendar += datetime.timedelta(days=1)
            days[last_day_of_calendar] = None
        qs = self.filter(**{
            '{}__gte'.format(attr_name): first_day_of_month,
            '{}__lte'.format(attr_name): last_day_of_month
        })
        total = {x:y for x, y in qs.values_list(attr_name).annotate(Count('id'))}
        for i, date in enumerate(days):
            if date in total:
                days[date] = total[date]
        last_day_of_previous_month = first_day_of_month - datetime.timedelta(days=1)
        first_day_of_previous_month = last_day_of_previous_month + datetime.timedelta(days=0)
        while first_day_of_previous_month.day > 1:
            first_day_of_previous_month = first_day_of_previous_month - datetime.timedelta(days=1)
        first_day_of_next_month = last_day_of_month + datetime.timedelta(days=1)
        last_day_of_next_month = first_day_of_next_month + datetime.timedelta(days=1)
        while last_day_of_next_month.month == first_day_of_next_month.month:
            last_day_of_next_month = last_day_of_next_month + datetime.timedelta(days=1)
        last_day_of_next_month = last_day_of_next_month - datetime.timedelta(days=1)
        selected_date = self.metadata['request'].GET.get('selected-date')
        if  selected_date:
            selected_date = datetime.datetime.strptime(selected_date, '%d/%m/%Y').date()
        # print(first_day_of_month, last_day_of_month)
        # print(first_day_of_previous_month, last_day_of_previous_month)
        # print(first_day_of_next_month, last_day_of_next_month)
        return dict(
            field=attr_name, days=days,
            previous=dict(first_day=first_day_of_previous_month, last_day=last_day_of_previous_month),
            next=dict(first_day=first_day_of_next_month, last_day=last_day_of_next_month),
            selected_date=selected_date, today=datetime.date.today()
        )

    # serialization function

    def to_list(self, wrap=False, verbose=False):
        data = []
        for obj in self:
            add_id = not wrap and not verbose
            actions = self.get_obj_actions(obj)
            if self.metadata['request'] and (obj.has_view_permission(self.metadata['request'].user) or obj.has_permission(self.metadata['request'].user)):
                actions.append('view')
            item = obj.values(*self._get_list_display(add_id=add_id)).load(verbose=verbose, size=False)
            data.append(dict(id=obj.id, description=str(obj), data=item, actions=actions) if wrap else item)
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
            if self.metadata['request'] is None or form_cls.check_fake_permission(
                    request=self.metadata['request'], instance=obj
            ):
                actions.append(form_cls.__name__)
        return actions

    def serialize(self, path=None, wrap=False, verbose=True, lazy=False):
        if wrap:
            if self.metadata['verbose_name']:
                verbose_name = self.metadata['verbose_name']
            elif self.metadata['attr']:
                verbose_name = pretty(self.metadata['attr'])
            else:
                verbose_name = pretty(self.model.metaclass().verbose_name_plural)

            for lookup in self.metadata['dfilters']:
                qs = self.order_by(lookup).values_list(lookup).distinct()[1:2]
                if not qs and lookup not in self.metadata['ignore']:
                    self.metadata['ignore'].append(lookup)

            icon = getattr(self.model.metaclass(), 'icon', None)
            search = self._get_search(verbose)
            display = self._get_display(verbose)
            filters = self._get_filters(verbose)
            attach = self._get_attach(verbose)
            calendar = self.to_calendar() if self.metadata['calendar'] and not lazy else None
            values = {} if lazy else self.paginate().to_list(wrap=wrap, verbose=verbose)
            pages = []
            n = self.count() // self._get_list_per_page() + 1
            for page in range(0, n):
                if page < 4 or (page > self.metadata['page'] - 3 and page < self.metadata['page'] + 1) or page > n - 5:
                    pages.append(page + 1)
            pagination = dict(
                interval=self.metadata['interval'],
                total=self.metadata['total'],
                page=self.metadata['page'],
                pages=pages
            )
            data = dict(
                uuid=self.metadata['uuid'], type='queryset',
                name=verbose_name, key=None, icon=icon, count=n,
                actions={}, metadata={}, data=values
            )
            if attach:
                data.update(attach=attach)
            if path is None:
                if self.metadata['request'] and self.metadata['request'].headers.get('x-requested-with') == 'XMLHttpRequest':
                    path = self.metadata['request'].path[4:]
                else:
                    path = '/{}/{}/'.format(self.model.metaclass().app_label, self.model.metaclass().model_name)
                    if self.metadata['attr']:
                        path = '{}{}/'.format(path, self.metadata['attr'])
            data.update(path=path)

            if not lazy:
                data['metadata'].update(
                    search=search, display=display, filters=filters, pagination=pagination,
                    collapsed=self.metadata['collapsed'], compact=self.metadata['compact'],
                    view=self.metadata['view'], is_admin=self.metadata['is_admin']
                )
                if calendar:
                    data['metadata']['calendar'] = calendar
                if self.metadata['totalizer']:
                    data['metadata'].update(total=self.sum(self.metadata['totalizer']))
                data['actions'].update(model=[], instance=[], queryset=[])
                data['actions']['instance'].append(
                    dict(
                        type='view', key='view', name='Visualizar', submit='Visualizar', target='instance',
                        method='get', icon='search', style='primary', ajax=False, path='{}{{id}}/'.format(path), modal=False
                    )
                )

                for action_type in ('global_actions', 'actions', 'batch_actions'):
                    for form_name in self.metadata[action_type]:
                        form_cls = self.model.action_form_cls(form_name)
                        if action_type == 'actions' or self.metadata['request'] is None or form_cls.check_fake_permission(
                                request=self.metadata['request'], instance=self.model(), instantiator=self._hints.get('instance')
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

    def is_admin(self):
        self.metadata['is_admin'] = True
        return self

    def totalizer(self, name):
        self.metadata['totalizer'] = name
        return self

    def verbose_name(self, name):
        self.metadata['verbose_name'] = pretty(name)
        return self

    def view(self, *names):
        self.metadata['view'] = list(names)
        return self

    def display(self, *names):
        self.metadata['display'] = list(names)
        return self

    def search(self, *names, q=None):
        self.metadata['search'] = list(names)
        if q:
            lookups = []
            for search_field in self._get_list_search() or self.model.default_search_fields():
                lookups.append(Q(**{'{}__icontains'.format(search_field): q}))
            return self.filter(reduce(operator.__or__, lookups))
        return self

    def filters(self, *names):
        self.metadata['filters'] = list(names)
        return self

    def dynamic_filters(self, *names):
        self.metadata['dfilters'] = list(names)
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

    def compact(self, flag=True):
        self.metadata['compact'] = flag
        return self

    def attr(self, name):
        self.metadata['attr'] = name
        if self.metadata['verbose_name'] is None:
            self.metadata['verbose_name'] = pretty(name)
        return self

    def source(self, name):
        self.metadata['source'] = name
        return self

    def page(self, n):
        self.metadata['page'] = n
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

    def paginate(self):
        if self.metadata['page'] != 1:
            start = (self.metadata['page'] - 1) * self._get_list_per_page()
            end = start + self._get_list_per_page()
            self.metadata['interval'] = '{} - {}'.format(start + 1, end)
            qs = self[start:end]
        else:
            self.metadata['interval'] = '{} - {}'.format(0 + 1, self._get_list_per_page())
            start = (self.metadata['page'] - 1) * self._get_list_per_page()
            end = start + self._get_list_per_page()
            self.metadata['interval'] = '{} - {}'.format(start + 1, end)
            qs = self.filter(pk__in=self.values_list('pk', flat=True)[start:end])

        if self.metadata['calendar'] and 'selected-date' in self.metadata['request'].GET:
            selected_date = self.metadata['request'].GET['selected-date']
            if selected_date:
                lookups = {self.metadata['calendar']: datetime.datetime.strptime(selected_date, '%d/%m/%Y')}
                qs = qs.filter(**lookups)

        return qs

    # rendering function

    def html(self):
        serialized = self.serialize(wrap=True, verbose=True)
        if self.metadata['source']:
            if hasattr(self.metadata['source'], 'model'):
                name = self.metadata['source'].model.metaclass().verbose_name_plural
            else:
                name = self.metadata['source']
            data = dict(
                type='object', name=str(name),
                icon=None, data={serialized['name']: serialized}, actions=[], attach=[], append={}
            )
            # print(json.dumps(data, indent=4, ensure_ascii=False))
            return render_to_string('app/valueset.html', dict(data=data), request=self.metadata['request'])
        return render_to_string(
            'app/queryset/queryset.html',
            dict(data=serialized, uuid=self.metadata['uuid'], messages=messages.get_messages(self.metadata['request'])),
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
                    component.html()
                )
            return self.apply_role_lookups(request.user)
        return self

    def process_request(self, request):
        from sloth.core.values import ValueSet
        page = 1
        attr_name = request.GET['subset']
        self.metadata['uuid'] = request.GET['uuid']
        attach = self if attr_name == 'all' else getattr(self, attr_name)()
        if isinstance(attach, QuerySet):
            qs = attach
            if self.metadata['ignore']:
                qs.metadata['ignore'] = self.metadata['ignore']
        elif isinstance(attach, QuerySetStatistics):
            qs = attach.qs
        elif isinstance(attach, ValueSet):
            qs = attach.instance
        else:
            raise Exception()
        qs.metadata.update(request=request)
        for item in self._get_filters().values():
            value = request.GET.get(item['key'])
            if value:
                if item['key'] == 'ordering':
                    qs = qs.order_by(value)
                else:
                    if item['type'] == 'date':
                        value = datetime.datetime.strptime(value, '%d/%m/%Y')
                    if item['type'] == 'boolean':
                        value = bool(int(value))
                    qs = qs.filter(**{item['key']: value})
        if 'q' in request.GET:
            qs = qs.search(q=request.GET['q'])
        if 'page' in request.GET:
            page = int(request.GET['page'] or 1)
        if isinstance(attach, QuerySet):
            if qs.metadata['attr'] is None and request.GET.get('subset') == 'all':
                qs.default_actions()
            qs = qs.page(page)
            # qs.debug()
            return qs
        if isinstance(attach, ValueSet):
            attach.instance = qs
            return attach
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

    def has_attr_permission(self, user, name):
        attr = getattr(self, 'has_{}_permission'.format(name), None)
        return attr is None or attr(user)

    # rendering template functions

    def cards(self):
        self.metadata['template'] = 'app/queryset/cards.html'
        return self

    def accordion(self):
        self.metadata['template'] = 'app/queryset/accordion.html'
        return self

    def datatable(self):
        self.metadata['template'] = 'app/queryset/datatable.html'
        return self

    def rows(self):
        self.metadata['template'] = 'app/queryset/rows.html'
        return self

    def timeline(self):
        self.metadata['template'] = 'app/queryset/timeline.html'
        return self
