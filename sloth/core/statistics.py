# -*- coding: utf-8 -*-

import json
from decimal import Decimal
from django.db.models.aggregates import Count
from sloth.exceptions import HtmlJsonReadyResponseException
from django.template.loader import render_to_string
from uuid import uuid1
from sloth.utils import pretty, colors


MONTHS = 'JAN', 'FEV', 'MAR', 'ABR', 'MAI', 'JUN', 'JUL', 'AGO', 'SET', 'OUT', 'NOV', 'DEZ'


class QuerySetStatistics(object):

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
        self.cursor = 0
        self.request = None
        self.metadata = dict(uuid='123456', attr=None, source=None, template='', verbose_name=None)

        if '__month' in x:
            self._xdict = {i + 1: month for i, month in enumerate(MONTHS)}
        if y and '__month' in y:
            self._ydict = {i + 1: month for i, month in enumerate(MONTHS)}

    def verbose_name(self, name):
        self.metadata['verbose_name'] = pretty(name)
        return self

    def contextualize(self, request):
        self.request = request
        if self.qs.request is None:
            self.qs.contextualize(request)
        self.qs = self.qs.apply_role_lookups(request.user) if request else self.qs
        if request and self.metadata['uuid'] == request.GET.get('uuid'):
            self.process_request(request)
        return self

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

    def attr(self, name):
        self.metadata['attr'] = name
        if self.metadata['verbose_name'] is None:
            self.metadata['verbose_name'] = pretty(name)
        return self

    def source(self, name):
        self.metadata['source'] = name
        return self

    def calc(self):
        self._values_dict = {}
        if self.y:
            values_list = self.qs.values_list(self.x, self.y).annotate(self.func(self.z))
        else:
            values_list = self.qs.values_list(self.x).annotate(self.func(self.z))

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

    def tabulate(self):
        self._calc()
        rows = []
        row = []
        row.append('')
        for info in self._xdict.values():
            row.append(info)
        rows.append(row)
        for i in self._xdict:
            row = []
            for j in self._ydict:
                if not row:
                    row.append(self._ydict[j])
                row.append(self._values_dict.get((i, j), 0))
            rows.append(row)
        return rows

    def filter(self, **kwargs):
        self._clear()
        self.qs = self.qs.filter(**kwargs)
        return self

    def apply_role_lookups(self, user):
        self._clear()
        self.qs = self.qs.apply_role_lookups(user)
        return self

    def debug(self):
        print(json.dumps(self.serialize(wrap=True, verbose=True), indent=4, ensure_ascii=False))

    def serialize(self, wrap=True, verbose=True, path=None, lazy=False):
        series = dict()
        verbose_name = self.metadata['verbose_name']
        if not lazy:
            self._calc()

            formatter = {True: 'Sim', False: 'Não', None: ''}

            def format_value(value):
                return float(value) if isinstance(value, Decimal) else value

            if self._ydict:
                for i, (yk, yv) in enumerate(self._ydict.items()):
                    data = []
                    self.cursor = 0
                    for j, (xk, xv) in enumerate(self._xdict.items()):
                        data.append([formatter.get(xv, str(self._xfield_display_value(xv))), format_value(self._values_dict.get((xk, yk), 0)), self.nex_color()])
                    series.update(**{formatter.get(yv, str(self._yfield_display_value(yv))): data})
            else:
                data = list()
                for j, (xk, xv) in enumerate(self._xdict.items()):
                    data.append([formatter.get(xv, str(self._xfield_display_value(xv))), format_value(self._values_dict.get((xk, None), 0)), self.nex_color()])
                if data:
                    series['default'] = data
        if self.request and path is None:
            prefix = self.request.path.split('/')[1]
            path = self.request.path.replace('/{}'.format(prefix), '')
        if wrap:
            return dict(
                type='statistics',
                uuid=self.metadata['uuid'],
                name=verbose_name,
                key=None,
                path=path,
                series=series,
                template=self.metadata['template'],
                normalized=self.normalize(series),
                # filters=self.qs.get_filters(verbose)
            )
        else:
            return series['default'] if 'default' in series else series

    def process_request(self, request):
        for item in self.qs.get_filters().values():
            value = request.GET.get(item['key'])
            if value:
                if item['type'] in ('date', 'datetime'):
                    value = datetime.datetime.strptime(value, '%d/%m/%Y')
                if item['type'] == 'boolean':
                    value = bool(int(value)) if value.isdigit() else value == 'true'
                self.qs = self.qs.filter(**{item['key']: value})
        raise HtmlJsonReadyResponseException(self.html())


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
            return render_to_string('app/valueset/valueset.html', dict(data=data), request=self.request)
        else:
            return render_to_string('app/statistics.html', dict(data=serialized), request=self.request)

    def __str__(self):
        return self.html() if self.request else super().__str__()

    def normalize(self, series):
        if 'default' in series:
            data = {'default': []}
            total = sum([item[1] for item in series['default']])
            start = 0
            for item in series['default']:
                percent = int(item[1] * 100 / total)
                end = start + percent
                data['default'].append(dict(
                    description=item[0], percentage=percent,
                    value=item[1], color=item[2], start=start, end=end
                ))
                start = end
        else:
            data = {}
            max_value = 0
            for key in series:
                max_value = max(max([item[1] for item in series[key]]), max_value)
            for key in series:
                data[key] = []
                total = sum([item[1] for item in series[key]])
                for item in series[key]:
                    data[key].append(dict(
                        description=item[0], percentage=int(item[1] * 100 / total if total else 0),
                        value=item[1], color=item[2]
                    ))
        return data

    def chart(self, name):
        self.metadata['template'] = 'app/charts/{}.html'.format(name)
        return self

    def pie_chart(self):
        return self.chart('pie')

    def donut_chart(self):
        return self.chart('donut')

    def bar_chart(self):
        return self.chart('bar')

    def column_chart(self):
        return self.chart('column')

    def nex_color(self):
        color = colors()[self.cursor]
        self.cursor += 1
        if self.cursor == len(colors()):
            self.cursor = 0
        return color

    def has_permission(self, user):
        return user.is_superuser or self.qs.has_permission(user)

