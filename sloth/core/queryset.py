# -*- coding: utf-8 -*-

import datetime
import json
import math
import operator
from functools import reduce
from uuid import uuid1
import zlib
import pickle
import base64
from django.core import signing
from django.conf import settings
from django.contrib import messages
from django.db import models
from django.db.models import Q
from django.db.models.aggregates import Sum, Count
from django.template.loader import render_to_string
from django.apps import apps
from sloth.utils.http import XlsResponse, CsvResponse
from sloth.core.statistics import QuerySetStatistics
from sloth.api.exceptions import JsonReadyResponseException, HtmlReadyResponseException, ReadyResponseException
from sloth.utils import getattrr, serialize, pretty, to_snake_case


class QuerySet(models.QuerySet):

    def __init__(self, *args, **kwargs):
        self.request = None
        self.metadata = None
        self.instantiator = None
        super().__init__(*args, **kwargs)
        self.reset()

    def reset(self):
        self.metadata = dict(uuid=uuid1().hex if self.model is None else self.model.__name__.lower(), subset=None,
            display=[], view=[], filters={}, dfilters={}, search=None,
            page=1, limit=20, interval='', total=0, ignore=[], only={}, is_admin=False, ordering=[],
            actions=[], attach=[], template=None, attr=None, source=None, aggregations=[], calendar=None,
            global_actions=[], batch_actions=[], inline_actions=[], lookups=[], collapsed=True, compact=False,
            verbose_name=None, related_field=None, scrollable=False
        )
        if self.model and getattr(self.model.metaclass(), 'autouser', False):
            self.lookups(autouser='pk')
            self.ignore('autouser')

    def _clone(self):
        clone = super()._clone()
        clone.request = self.request
        clone.instantiator = self.instantiator
        clone.metadata = dict(self.metadata)
        return clone

    def first(self):
        obj = super().first()
        if self.metadata['related_field'] and isinstance(obj, self.model):
            obj.related_field = self.metadata['related_field']
        return obj

    def related_field(self, name):
        self.metadata['related_field'] = name
        return self.ignore(name)

    def role_lookups(self, *names, **scopes):
        for name in names:
            self.metadata['lookups'].append((name, scopes))
        return self

    def lookups(self, name='Usuário', *names, **scopes):
        self.role_lookups(*((name,) + names), **scopes)
        return self

    def readonly(self):
        for key in ('actions', 'inline_actions', 'batch_actions'):
            self.metadata[key].clear()
        return self

    def has_permission(self, user):
        if user.is_authenticated:
            return user.is_superuser or user.roles.contains(*(t[0] for t in self.metadata['lookups']))
        return False

    def has_attr_permission(self, user, name):
        if user.is_superuser:
            return True
        qs = self.model.objects
        if name == 'all' or name in qs.metadata['attach']:
            return qs.has_permission(user)
        return getattr(self._clone(), name)().has_permission(user)

    def get_allowed_attrs(self, recursive=True):
        allowed = []
        for key in ('global_actions', 'actions', 'batch_actions', 'inline_actions'):
            allowed.extend(self.metadata[key])
        allowed.extend(self.metadata['attach'])
        if recursive:
            for attach in self.metadata['attach']:
                allowed.extend(getattr(self._clone(), attach)().get_allowed_attrs(recursive=False))
        for view in self.metadata['view']:
            allowed.append('view' if view['name'] == 'self' else view['name'])
        return allowed

    def apply_role_lookups(self, user):
        if user.is_superuser:
            return self
        else:
            for field_name, role_names in self.metadata['only'].items():
                if not self.request.user.roles.contains(*role_names):
                    self.ignore(field_name)
        if self.metadata['lookups']:
            lookups = []
            for name, scopes in self.metadata['lookups']:
                if scopes:
                    for scope_value_attr, scope_key in scopes.items():
                        for scope_value in user.roles.filter(active=True, name=name, scope_key=scope_key).values_list('scope_value', flat=True):
                            lookups.append(Q(**{scope_value_attr: scope_value}))
                else:
                    if user.roles.contains(name):
                        return self
            if lookups:
                return self.filter(reduce(operator.__or__, lookups))
        return self.none() if self.metadata['is_admin'] else self

    def append(self, *names):
        from sloth.core.valueset import ValueSet
        return ValueSet(self, names)

    def value_set(self, *names):
        from sloth.core.valueset import ValueSet
        return ValueSet(self, names)

    def get_list_display(self, add_id=False):
        if self.metadata['display']:
            list_display = self.metadata['display']
        else:
            list_display = self.model.default_list_fields()
        display = [name for name in list_display if name not in self.metadata['ignore']]
        if add_id:
            display.insert(0, 'id')
        return display

    def get_list_filters(self):
        if self.metadata['filters'] is None:
            list_filter = []
        elif self.metadata['filters']:
            list_filter = self.metadata['filters']
        else:
            list_filter = self.model.default_filter_fields()
        return [name for name in list_filter if name not in self.metadata['ignore']]

    def get_search(self):
        search = {}
        if self.metadata['search'] is None:
            for lookup in self.metadata['search'] or self.model.default_search_fields():
                verbose_name = self.model.get_attr_metadata(lookup)[0]
                search[lookup] = dict(key=lookup, name=verbose_name)
        return search

    def get_display(self):
        display = {}
        for lookup in self.get_list_display():
            verbose_name, sort, _, _ = self.model.get_attr_metadata(lookup)
            display[lookup] = dict(
                key=lookup, name=pretty(verbose_name), sort=sort#, template=template, metadata=metadata
            )
        return display

    def filter_form_cls(self):
        return self.get_filters(as_form=True)

    def get_filters(self, as_form=False):
        from sloth import actions
        filters = {}
        list_filter = self.get_list_filters()
        list_filter.extend(self.metadata['dfilters'])
        if self.metadata['calendar']:
            list_filter.append(self.metadata['calendar'])
        for lookup in list_filter:
            field = self.model.get_field(lookup)
            formfield = field.formfield()
            filter_type = 'choices'
            if isinstance(formfield, actions.BooleanField):
                filter_type = 'boolean'
            elif isinstance(formfield, actions.DateTimeField):
                filter_type = 'datetime'
            elif isinstance(formfield, actions.DateField):
                filter_type = 'date'
            if lookup in self.metadata['dfilters']:
                qs = self.order_by(lookup).values_list(lookup).distinct()[1:2]
                if not qs:
                    continue

            key = lookup
            name = pretty(str(field.verbose_name))
            if filter_type in ('datetime', 'date'):
                for sublookup, symbol in dict(gte='>', lte='<').items():
                    k = '{}__{}'.format(key, sublookup)
                    n = '{} {}'.format(symbol, name)
                    hidden = lookup == self.metadata['calendar']
                    formfield = field.formfield(label=n, required=False)
                    fkey = '{}__{}'.format(lookup, sublookup)
                    filters[k] = dict(key=fkey, name=n, type=filter_type, choices=None, hidden=hidden, value=self.request.GET.get(fkey) if self.request else None
                    )
            elif filter_type == 'choices':
                value = None
                if self.request and self.request.GET.get(lookup):
                    value = [self.request.GET.get(f'{lookup}0'), self.request.GET.get(lookup)]
                filters[key] = dict(key=lookup, name=name, type=filter_type, choices=None, hidden=False, value=value)
            else:
                filters[key] = dict(
                    key=lookup, name=name, type=filter_type, choices=None, hidden=False, value=self.request.GET.get(lookup) if self.request else None
                )
            if as_form:
                filters[key].update(formfield=formfield)
            if filter_type == 'boolean':
                filters[key]['value'] = int(filters[key]['value']) if filters[key]['value'] else None

        ordering = []
        for lookup in self.metadata['ordering']:
            field = self.model.get_field(lookup)
            ordering.append(dict(id=lookup, text=field.verbose_name))
        if ordering:
            value = None
            key = 'ordering'
            if self.request and self.request.GET.get(key):
                value = [self.request.GET.get(f'{key}0'), self.request.GET.get(key)]
            filters[key] = dict(
                key='ordering', name='Ordenação', type='choices', choices=ordering, value=value
            )
            if as_form:
                choices = [(o['id'], [o['text']]) for o in ordering]
                filters[key].update(formfield=actions.ChoiceField(label='Ordenação', choices=choices, required=False))

        if as_form:
            class FilterForm(actions.Action):

                class Meta:
                    pass

                def __init__(self, *args, **kwargs):
                    super().__init__(*args, **kwargs)
                    for key in filters:
                        self.fields[key] = filters[key]['formfield']

            return FilterForm

        return filters

    def get_attach(self):
        if isinstance(self.metadata['attach'], dict):
            return self.metadata['attach']
        attaches = {}
        if self.metadata['attach'] and not self.query.is_sliced:
            for i, name in enumerate(['all'] + self.metadata['attach']):
                attr = getattr(self._clone(), name)
                attach = attr()
                if self.request and hasattr(attach, 'apply_role_lookups'):
                    attach = attach.apply_role_lookups(self.request.user)
                if hasattr(attr, '__verbose_name__'):
                    verbose_name = attr.__verbose_name__
                else:
                    verbose_name = attach.metadata['verbose_name'] or pretty(name)
                active = self.request.GET.get('subset', 'all') if self.request else 'all'
                if isinstance(attach, QuerySet):
                    if verbose_name.lower() == 'all':
                        verbose_name = 'Tudo'
                    attaches[name] = dict(
                        name=verbose_name, key=name, count=attach.count(), active=name == active
                    )
                else:
                    attaches[name] = dict(
                        name=verbose_name, key=name, active=name == active
                    )
        self.metadata['attach'] = attaches
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
        start = self.request.GET.get('{}__gte'.format(attr_name))
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
            '{}__lt'.format(attr_name): last_day_of_month + datetime.timedelta(days=i)
        })
        total = {}
        for k, v in [(x.date() if hasattr(x, 'date') else x, y) for x, y in qs.values_list(attr_name).annotate(Count('id'))]:
            if k in total:
                total[k] += v
            else:
                total[k] = v
        for i, date in enumerate(days):
            if date in total:
                days[date] += total[date]
        last_day_of_previous_month = first_day_of_month - datetime.timedelta(days=1)
        first_day_of_previous_month = last_day_of_previous_month + datetime.timedelta(days=0)
        while first_day_of_previous_month.day > 1:
            first_day_of_previous_month = first_day_of_previous_month - datetime.timedelta(days=1)
        first_day_of_next_month = last_day_of_month + datetime.timedelta(days=1)
        last_day_of_next_month = first_day_of_next_month + datetime.timedelta(days=1)
        while last_day_of_next_month.month == first_day_of_next_month.month:
            last_day_of_next_month = last_day_of_next_month + datetime.timedelta(days=1)
        last_day_of_next_month = last_day_of_next_month - datetime.timedelta(days=1)
        selected_date = self.request.GET.get('selected-date')
        if selected_date:
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

    def to_list(self, wrap=False, detail=True):
        data = []
        for obj in self:
            add_id = not wrap
            actions = self.get_obj_actions(obj)
            if self.request:
                for view in self.metadata['view']:
                    if view['name'] == 'self':
                        has_view_permission = obj.has_view_permission(self.request.user)
                    else:
                        has_view_permission = obj.has_view_attr_permission(self.request.user, view['name'])
                    if self.request.user.is_superuser or has_view_permission or obj.has_permission(self.request.user):
                        actions.append(view['name'])
            item = obj.value_set(*self.get_list_display(add_id=add_id)).contextualize(self.request).load(wrap=False, detail=detail)
            data.append(dict(id=obj.id, description=str(obj), data=item, actions=actions) if wrap else item)
        return data

    def export(self, limit=100):
        data = []
        header = []
        for i, obj in enumerate(self[0:limit]):
            if i == 0:
                for attr_name in self.get_list_display():
                    attr, value = getattrr(obj, attr_name)
                    header.append(pretty(self.model.get_attr_metadata(attr_name)[0]).upper())
                data.append(header)
            row = []
            values = obj.value_set(*self.get_list_display()).load(wrap=False, detail=False).values()
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
            if form_cls is None:
                raise BaseException('Action does not exist: {}'.format(form_name))
            if self.request is None or form_cls.check_fake_permission(
                    request=self.request, instance=obj
            ):
                actions.append(form_cls.get_api_name())
        return actions

    def serialize(self, path=None, wrap=False, lazy=False):
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

            total = self.count()
            icon = getattr(self.model.metaclass(), 'icon', None)
            search = self.get_search()
            display = self.get_display()
            filters = self.get_filters()
            attach = self.get_attach() if self.metadata['attr'] is None else {}
            calendar = self.to_calendar() if self.metadata['calendar'] and not lazy else None
            values = {} if lazy else self.paginate().to_list(wrap=wrap, detail=True)
            pages = []
            n_pages = ((total-1) // self.metadata['limit']) + 1
            for page in range(0, n_pages):
                if page < 4 or (page > self.metadata['page'] - 3 and page < self.metadata['page'] + 1) or page > n_pages - 5:
                    pages.append(page + 1)
            pagination = dict(
                interval=self.metadata['interval'],
                total=total,
                page=self.metadata['page'],
                pages=pages
            )
            data = dict(
                uuid=self.metadata['uuid'], type='queryset', path=path,
                name=verbose_name, key=self.metadata['uuid'], icon=icon, count=n_pages,
                actions={}, metadata={}, data=values
            )
            if self.request and self.request.path.startswith('/app/'):
                data.update(instantiator=self.instantiator)
            if attach:
                data.update(attach=attach)

            if not lazy:
                collapsed = bool(self.request and self.request.GET.get('collapsed', self.metadata['collapsed']) or 0)
                subset = self.request and self.request.GET.get('subset', 'all') or 'all'
                data['metadata'].update(
                    search=search, display=display, filters=filters, pagination=pagination,
                    collapsed=collapsed, subset=subset,
                    compact=self.metadata['compact'], is_admin=self.metadata['is_admin']# , state=self.dumps()
                )
                if calendar:
                    data['metadata']['calendar'] = calendar

                if self.metadata['aggregations']:
                    aggregations = {}
                    for aggregation in self.metadata['aggregations']:
                        aggregations[aggregation] = dict(
                            name=pretty(self.get_attr_metadata(aggregation)[0]),
                            value=getattr(self, aggregation)()
                        )
                    data['metadata'].update(aggregations=aggregations)
                if self.metadata['scrollable']:
                    data['metadata'].update(scrollable=True)

                data['actions'].update(model=[], instance=[], queryset=[], inline=[])

                for view in self.metadata['view']:
                    if view['name'] == 'self':
                        view_suffix = ''
                        view_name = 'Visualizar'
                    else:
                        view_suffix = '{}/'.format(view['name'])
                        view_name = pretty(self.model.get_attr_metadata(view['name'])[0])
                    data['actions']['instance'].append(
                        dict(
                            type='view', key=view['name'], name=view_name, submit=view_name, target='instance',
                            method='get', icon=view['icon'], style='primary', ajax=False,
                            modal=view['modal'], path='{}{{id}}/{}'.format((path or '').split('?')[0], view_suffix)
                        )
                    )
                for action_type in ('global_actions', 'actions', 'batch_actions', 'inline_actions'):
                    target = dict(global_actions='model', actions='instance', batch_actions='queryset', inline_actions='inline')[action_type]
                    for form_name in self.metadata[action_type]:
                        if form_name == 'view':
                            continue
                        form_cls = self.model.action_form_cls(form_name)
                        has_permission = self.request is None or form_cls.check_fake_permission(
                            request=self.request, instance=self.model(), instantiator=self._hints.get('instance')
                        )
                        if action_type == 'actions' or has_permission:
                            action_path = path
                            if self.request and self.request.GET.get('subset'):
                                action_path = '{}{}/'.format(path, self.request.GET.get('subset'))
                            action = form_cls.get_metadata(path, target)
                            data['actions'][action['target']].append(action)
                if self.metadata['related_field']:
                    form_cls = self.model.relation_form_cls(self.metadata['related_field'])
                    has_permission = self.request is None or form_cls.check_fake_permission(
                        request=self.request, instance=self.model(), instantiator=self._hints.get('instance')
                    )
                    if has_permission:
                        action = form_cls.get_metadata(path, 'model')
                        data['actions']['model'].append(action)

                template = self.metadata['template']
                if template is None:
                    template = getattr(self.model.metaclass(), 'list_template', None)
                if template:
                    template = template if template.endswith('.html') else '{}.html'.format(template)
                    data.update(template=template)
            # from pprint import pprint; pprint(data)
            return data
        return self.to_list(detail=False)

    def debug(self):
        print(json.dumps(self.serialize(wrap=True), indent=4, ensure_ascii=False))

    # metadata functions

    def admin(self):
        self.metadata['is_admin'] = True
        return self

    def aggregations(self, *names):
        self.metadata['aggregations'].extend(names)
        return self

    def verbose_name(self, name):
        # self.metadata['uuid'] = slugify(name).replace('-', '_')
        self.metadata['verbose_name'] = pretty(name)
        return self

    def preview(self, *names, modal=True, icon=None):
        for name in names:
            if name:
                self.metadata['view'] = list(self.metadata['view'])
                self.metadata['view'].append(dict(name=name, modal=modal, icon=icon))
            else:
                self.metadata['view'].clear()
        return self

    def view(self):
        return self.all()

    def display(self, *names, add_default=False):
        if add_default:
            names = tuple(self.model.default_list_fields()) + names
        self.metadata['display'] = list(names)
        return self

    def search(self, *names, q=None):
        if q is not None:
            lookups = []
            for search_field in self.metadata['search'] or self.model.default_search_fields():
                lookups.append(Q(**{'{}__icontains'.format(search_field): q}))
            return self.filter(reduce(operator.__or__, lookups))
        else:
            self.metadata['search'] = list(names) if names else []
        return self

    def filters(self, *names):
        self.metadata['filters'] = list(names) if names else None
        return self

    def dynamic_filters(self, *names):
        self.metadata['dfilters'] = list(names) if names else None
        return self

    def ordering(self, *names):
        self.metadata['ordering'] = list(names)
        return self

    def limit_per_page(self, size):
        self.metadata['limit'] = size
        return self

    def renderer(self, name):
        self.metadata['template'] = name
        return self

    def attach(self, *names):
        qs = self._clone()
        qs.metadata['attach'] = list(names)
        return qs

    def ignore(self, *names):
        self.metadata['ignore'] = list(names)
        return self

    def only(self, *names, **kwargs):
        if kwargs:
            for name, role in kwargs.items():
                if name not in self.metadata['only']:
                    self.metadata['only'][name] = []
                self.metadata['only'][name].append(role)
            return self
        return super().only(*names)

    def collapsed(self, flag=True):
        self.metadata['collapsed'] = flag
        return self

    def expand(self):
        return self.collapsed(False)

    def template(self, name):
        self.metadata['template'] = name if '.html' in name else '{}.html'.format(name)
        return self

    def compact(self, flag=True):
        self.metadata['compact'] = flag
        return self

    def attr(self, name, source=False):
        self.metadata['attr'] = name
        self.metadata['uuid'] = name
        if self.metadata['verbose_name'] is None:
            self.metadata['verbose_name'] = self.get_attr_metadata(name)[0]
        if source:
            self.metadata['is_admin'] = True
            self.metadata['collapsed'] = False
            self.metadata['verbose_name'] = self.get_attr_metadata(name)[0]
        return getattr(self._clone(), name)()

    @classmethod
    def get_attr_metadata(cls, lookup):
        attr = getattr(cls, lookup)
        template = getattr(attr, '__template__', None)
        metadata = getattr(attr, '__metadata__', None)
        if template:
            if not template.endswith('.html'):
                template = '{}.html'.format(template)
            if not template.startswith('.html'):
                template = 'renderers/{}'.format(template)
        return getattr(attr, '__verbose_name__', pretty(lookup)), False, template, metadata

    def source(self, name):
        self.metadata['source'] = name
        return self

    def page(self, n):
        self.metadata['page'] = n
        return self

    # action functions

    def actions(self, *names, clear=False):
        if clear:
            self.metadata['actions'].clear()
        for name in names:
            if name == 'view':
                self.metadata['view'].append(dict(name='self', modal=False, icon='search'))
            elif to_snake_case(name) not in self.metadata['actions']:
                self.metadata['actions'].append(to_snake_case(name))
        return self

    def global_actions(self, *names, clear=False):
        if clear:
            self.metadata['global_actions'].clear()
        self.metadata['global_actions'].extend(
            [to_snake_case(name) for name in names if to_snake_case(name) not in self.metadata['global_actions']]
        )
        return self

    def batch_actions(self, *names, clear=False):
        if clear:
            self.metadata['batch_actions'].clear()
        self.metadata['batch_actions'].extend(
            [to_snake_case(name) for name in names if to_snake_case(name) not in self.metadata['batch_actions']]
        )
        return self

    def inline_actions(self, *names, clear=False):
        if clear:
            self.metadata['inline_actions'].clear()
        self.metadata['inline_actions'].extend(
            [to_snake_case(name) for name in names if to_snake_case(name) not in self.metadata['inline_actions']]
        )
        return self

    def default_actions(self):
        if self.metadata['attr'] is None:
            self.actions('view', 'edit', 'delete')
            self.global_actions('add')
        return self

    # search and pagination functions

    def get_ordering(self):
        ordering = self.request.GET.get('ordering') if self.request else None
        if ordering:
            return [ordering]
        else:
            return self.query.order_by or ['id']

    def scrollable(self, flag=True):
        self.metadata['scrollable'] = flag
        return self.datatable()

    def paginate(self):
        qs = self
        if self.metadata['calendar'] and 'selected-date' in self.request.GET:
            selected_date = self.request.GET['selected-date']
            if selected_date:
                lookups = {
                    '{}__gte'.format(self.metadata['calendar']): datetime.datetime.strptime(selected_date, '%d/%m/%Y').date(),
                    '{}__lt'.format(self.metadata['calendar']): datetime.datetime.strptime(selected_date, '%d/%m/%Y').date() + datetime.timedelta(days=1)
                }
                qs = qs.filter(**lookups)

        if self.metadata['page'] != 1:
            start = (self.metadata['page'] - 1) * self.metadata['limit']
            end = start + self.metadata['limit']
            self.metadata['interval'] = (start + 1, end)
            qs = qs.order_by(*self.get_ordering())[start:end]
        else:
            self.metadata['interval'] = 0 + 1, self.metadata['limit']
            start = (self.metadata['page'] - 1) * self.metadata['limit']
            end = start + self.metadata['limit']
            self.metadata['interval'] = start + 1, end
            qs = qs.filter(pk__in=self.values_list('pk', flat=True)).order_by(*self.get_ordering())[start:end]
        return qs

    # rendering function

    def html(self, path=None, print=False):
        serialized = self.serialize(path=path or self.request.path, wrap=True)
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
            return render_to_string('valueset/valueset.html', dict(data=data), request=self.request)
        return render_to_string(
            'queryset/queryset.html',
            dict(data=serialized, uuid=self.metadata['uuid'], messages=messages.get_messages(self.request), print=print),
            request=self.request
        )

    def __str__(self):
        if self.request:
            return self.html()
        return super().__str__()

    # request functions
    def contextualize(self, request):
        self.request = request
        if request and request.user.is_superuser and 'autouser' in self.metadata['ignore']:
            self.metadata['ignore'].remove('autouser')
        if request and self.metadata['uuid'] == request.GET.get('uuid'):
            if 'choices' in request.GET:
                raise JsonReadyResponseException(
                    self.process_request(request).choices(request)
                )
            component = self.process_request(request).apply_role_lookups(request.user)
            if request.path.startswith('/app/'):
                raise HtmlReadyResponseException(component.html())
            else:
                meta = request.path.startswith('/meta/')
                raise JsonReadyResponseException(component.serialize(wrap=meta))
            return self.apply_role_lookups(request.user)
        return self

    def process_request(self, request):
        from sloth.core.valueset import ValueSet
        page = 1
        attr_name = request.GET.get('subset', 'all')
        self.metadata['uuid'] = request.GET.get('uuid')
        if attr_name == 'all':
            attach = self
        else:
            attaches = self.get_attach()
            self.metadata['subset'] = attr_name
            attach = getattr(self._clone(), attr_name)()
            attach.metadata['attach'] = attaches
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
        if request.path.startswith('/app/'):
            qs.metadata.update(request=request)
        for item in qs.get_filters().values():
            value = request.GET.get(item['key'])
            if value:
                if item['key'] == 'ordering':
                    qs = qs.order_by(value)
                else:
                    if item['type'] in ('date', 'datetime'):
                        value = datetime.datetime.strptime(value, '%d/%m/%Y' if '/' in value else '%Y-%m-%d')
                    if item['type'] == 'boolean':
                        value = bool(int(value)) if value.isdigit() else value == 'true'
                    if item['key'] != request.GET.get('choices'):
                        qs = qs.filter(**{item['key']: value})
        if 'q' in request.GET:
            qs = qs.search(q=request.GET['q'])
        if 'page' in request.GET:
            page = int(request.GET['page'] or 1)
        if isinstance(attach, QuerySet):
            # if request.GET.get('is_admin') and qs.metadata['attr'] is None and request.GET.get('subset') == 'all':
            #     qs.default_actions()
            qs = qs.page(page)
            # qs.debug()
            return qs.distinct()
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
            return statistcs.contextualize(self.request)
        total = super().count()
        return total

    def sum(self, z, x=None, y=None):
        if x:
            if y:
                statistcs = QuerySetStatistics(self, x, y=y, func=Sum, z=z)
            else:
                statistcs = QuerySetStatistics(self, x, func=Sum, z=z)
            return statistcs.contextualize(self.request)
        return self.aggregate(sum=Sum(z))['sum'] or 0

    # rendering template functions

    def cards(self):
        self.metadata['template'] = 'queryset/cards.html'
        return self

    def accordion(self):
        self.metadata['template'] = 'queryset/accordion.html'
        return self

    def datatable(self):
        self.metadata['template'] = 'queryset/datatable.html'
        return self

    def rows(self):
        self.metadata['template'] = 'queryset/rows.html'
        return self

    def timeline(self):
        self.metadata['template'] = 'queryset/timeline.html'
        return self

    def normalize_email(self, email):
        return email

    def dumps(self, add_metadata=True):
        request = self.metadata.pop('request', None)
        state = dict(app=self.model.metaclass().app_label, model=self.model.metaclass().model_name, query=self.query)
        if add_metadata:
            state.update(metadata=self.metadata)
        s = signing.dumps(base64.b64encode(zlib.compress(pickle.dumps(state))).decode())
        if request:
            self.metadata['request'] = request
        return s

    @staticmethod
    def loads(s):
        state = pickle.loads(zlib.decompress(base64.b64decode(signing.loads(s).encode())))
        model = apps.get_model(state['app'], state['model'])
        query = state['query']
        queryset = model.objects.none()
        queryset.query = query
        queryset.metadata = state['metadata']
        return queryset

    def action_form_cls(self, action):
        return self.model.action_form_cls(action)

    def get_full_path(self):
        pass
