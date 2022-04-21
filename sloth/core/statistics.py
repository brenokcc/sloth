# -*- coding: utf-8 -*-

import json
from decimal import Decimal

from django.db.models.aggregates import Count
from django.template.loader import render_to_string

from sloth.utils import pretty

COLORS = '#DECF3F', '#5DA5DA', '#B276B2', '#F15854', '#4D4D4D', '#B276B2'
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
        self.metadata = dict(request=None, attr=None, template='', verbose_name=None)

        if '__month' in x:
            self._xdict = {i + 1: month for i, month in enumerate(MONTHS)}
        if y and '__month' in y:
            self._ydict = {i + 1: month for i, month in enumerate(MONTHS)}

    def verbose_name(self, name):
        self.metadata['verbose_name'] = pretty(name)
        return self

    def contextualize(self, request):
        self.metadata.update(request=request)
        if request:
            self.qs = self.qs.apply_role_lookups(request.user)
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
        if not lazy:
            self._calc()
        series = dict()
        formatter = {True: 'Sim', False: 'Não', None: ''}
        verbose_name = self.metadata['verbose_name']

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

        return dict(
            type='statistics',
            name=verbose_name,
            path=path,
            series=series,
            template=self.metadata['template'],
            normalized=self.normalize(series)
        )

    def html(self, uuid=None, request=None):
        data = self.serialize(wrap=True, verbose=True)
        return render_to_string('adm/statistics.html', dict(data=data))

    def __str__(self):
        if self.metadata['request']:
            return self.html()
        return super().__str__()

    def normalize(self, series):
        if 'default' in series:
            data = {'default': []}
            total = sum([item[1] for item in series['default']])
            for item in series['default']:
                data['default'].append(dict(
                    description=item[0], percentage=int(item[1] * 100 / total),
                    value=item[1], color=item[2]
                ))
        else:
            data = {}
            max_value = 0
            for key in series:
                max_value = max(max([item[1] for item in series[key]]), max_value)
            for key in series:
                data[key] = []
                for item in series[key]:
                    data[key].append(dict(
                        description=item[0], percentage=int(item[1] * 100 / max_value),
                        value=item[1], color=item[2]
                    ))
        return data

    def chart(self, name):
        self.metadata['template'] = 'adm/charts/{}.html'.format(name)
        return self

    def nex_color(self):
        color = COLORS[self.cursor]
        self.cursor += 1
        if self.cursor == len(COLORS):
            self.cursor = 0
        return color
