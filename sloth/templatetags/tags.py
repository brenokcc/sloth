# -*- coding: utf-8 -*-
import datetime
from decimal import Decimal

from django.conf import settings
from django.db.models.fields.files import FieldFile
from django.template import Library
from django.utils.safestring import mark_safe

register = Library()


@register.filter('format')
def _format(obj):
    if obj is not None:
        if isinstance(obj, str):
            return obj
        elif isinstance(obj, bool):
            return 'Sim' if obj else 'Não'
        elif isinstance(obj, datetime.datetime):
            return obj.strftime('%d/%m/%Y %H:%M')
        elif isinstance(obj, datetime.date):
            return obj.strftime('%d/%m/%Y')
        elif isinstance(obj, float):
            return format_decimal(obj)
        elif isinstance(obj, list):
            return mark_safe(
                '<ul>{}</ul>'.format(''.join(['<li>{}</li>'.format(o) for o in obj]))
            )
        elif hasattr(obj, 'all'):
            return mark_safe(
                '<ul>{}</ul>'.format(''.join(['<li>{}</li>'.format(o) for o in obj]))
            )
        elif isinstance(obj, dict):
            return mark_safe(
                '<dl>{}</dl>'.format(''.join(['<dt>{}</dt><dd>{}</dd>'.format(k, v) for k, v in obj.items()]))
            )
        elif isinstance(obj, FieldFile):
            return obj.url
        return str(obj)
    return '-'


def format_decimal(value, decimal_places=2):
    str_format = '{{:,.{}f}}'.format(decimal_places)
    if value is not None:
        value = str_format.format(Decimal(value))
        if settings.LANGUAGE_CODE == 'pt-br':
            value = value.replace(',', '#').replace('.', ',').replace('#', '.')
    return value


def format_decimal3(value):
    if value is None:
        return ''
    return format_decimal(value, 3)


def format_decimal1(value):
    if value is None:
        return ''
    return format_decimal(value, 1)


@register.filter
def index(indexable, i):
    return indexable[i]


@register.filter
def mobile(request):
    if request:
        width = int(request.COOKIES.get('width', 0))
        return width if width < 600 else False
    return False


@register.filter
def tablet(request):
    if request:
        width = int(request.COOKIES.get('width', 0))
        return width if 600 < width < 800 else False
    return False


@register.filter
def formfield(form, name):
    return form[name]


@register.filter
def label_tag(html):
    return mark_safe(html.replace(':', ''))


@register.filter
def isupper(text):
    return text and text.isupper()


@register.filter
def is_one_to_one_field_controller(name):
    return name and name.isupper() and name.count('--') == 0


@register.filter
def is_one_to_many_field_controller(name):
    return name and name.isupper() and name.count('--') == 1


@register.filter
def is_controller_field(name):
    return is_one_to_one_field_controller(name) or is_one_to_many_field_controller(name)


@register.filter
def image_src(path):
    if path:
        path = str(path)
        if path.startswith('/') or path.startswith('http'):
            return path
        return '/media/{}'.format(path)
    return '/static/images/no-image.png'


@register.filter
def image_key(dictionary):
    for k, v in dictionary.items():
        if v and isinstance(v, str) and v.split('.')[-1].lower() in ('png', 'jpg', 'jpeg'):
            return k
    return None


@register.filter
def column_chart_height(percentage):
    return 3*int(percentage)


@register.filter
def column_chart_serie_width(data):
    for series in data.values():
        return 100 * len(series)


@register.filter
def column_chart_series_width(data):
    width = 0
    for series in data.values():
        for _ in series:
            width += 100
    return width


@register.filter
def column_chart_width(data):
    return column_chart_series_width(data) + 100


@register.filter
def multiply(value, n):
    return value * n


@register.filter
def add(value, n):
    return value + n

